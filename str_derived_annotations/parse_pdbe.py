import typing
from pathlib import Path

import intervaltree as it
import prody as pd

import requests as rq
import gzip
import xml.etree.ElementTree as ET
import ftplib


from utils.uniprot import seq_from_ac

MAPPING_FILE = "uniprot_segments_observed.tsv"


def get_sequences_from_fasta_yield(fasta_file: typing.Union[str, Path]) -> tuple:
    """
    Returns (accession, sequence) iterator
    Parameters
    ----------
    fasta_file
    Returns
    -------
    (accession, sequence)
    """
    with open(fasta_file) as f:
        current_sequence = ""
        current_key = None
        for line in f:
            if not len(line.strip()):
                continue
            if "==" in line:
                continue
            if ">" in line:
                if current_key is None:
                    current_key = line.split(">")[1].strip()
                else:
                    yield (current_key, current_sequence)
                    current_sequence = ""
                    current_key = line.split(">")[1].strip()
            else:
                current_sequence += line.strip()
        yield (current_key, current_sequence)


def get_sequences_from_fasta(fasta_file: typing.Union[str, Path]) -> dict:
    """
    Returns dict of accession to sequence from fasta file
    Parameters
    ----------
    fasta_file
    Returns
    -------
    {accession:sequence}
    """
    return {key: sequence for (key, sequence) in get_sequences_from_fasta_yield(fasta_file)}


def parse_pdbe_mapping_file() -> dict:
    """
    A summary of the UniProt to PDBe residue level mapping (observed residues only),
    showing the start and end residues of the mapping using SEQRES, PDB sequence and UniProt numbering.

    Returns
    -------
    dict of (pdb_id, chain_id): dict of (SP_PRIMARY, RES_BEG, RES_END, PDB_BEG, PDB_END, SP_BEG, SP_END)
    """

    column_names = None
    residue_mapping = {}
    with open(MAPPING_FILE) as f:
        for i, line in enumerate(f):
            if i == 0:
                continue
            elif i == 1:
                column_names = line.strip().split("\t")
            else:
                parts = line.strip().split("\t")
                residue_mapping[(parts[0], parts[1])] = dict(zip(column_names[2:], parts[2:]))
    return residue_mapping


class UniProtBasedMapping:
    def __init__(self, uniprot_id: str):
        self.uniprot_id = uniprot_id
        self.all_residue_mapping = parse_pdbe_mapping_file()
        self.PDBe_api_request_url = f"https://www.ebi.ac.uk/pdbe/api/mappings/best_structures/{uniprot_id}"
        self.uniprot_api_request_url = f"https://www.ebi.ac.uk/uniprot/api/covid-19/uniprotkb/accession/{uniprot_id}.gff"
        self.uniprot_sequence = seq_from_ac(uniprot_id)
        self.protein_annotation_intervals = dict()
        self._get_intervals_from_uniprot()
        self.data = {x["pdb_id"]: x for x in rq.get(self.PDBe_api_request_url).json()[uniprot_id]}
        self.tree = it.IntervalTree()
        self._build_tree()

    def list_available_annotations(self):
        print('\n'.join(list(self.protein_annotation_intervals.keys())))

    def _build_tree(self):
        for pdb_id, data in self.data.items():
            self.tree[data["unp_start"]: data["unp_end"]] = pdb_id

    def _get_intervals_from_uniprot(self):
        gff_lines = [x for x in rq.get(self.uniprot_api_request_url).text.split("\n") if not x.startswith("#") and len(x)]
        for line in gff_lines:
            line = line.split("\t")
            _range = (int(line[3]), int(line[4]))
            info = line[-2].split(";")
            note = [x for x in info if x.startswith("Note")]
            if len(note):
                protein_id = note[0].split("=")[-1]
                self.protein_annotation_intervals[protein_id] = _range
            else:
                continue

    def search_pdbs_by_protein_name(self, annotation_name):
        try:
            start, end = self.protein_annotation_intervals[annotation_name]
        except KeyError:
            raise KeyError(f"No such protein name found. here are the available ones: \
            {', '.join(list(self.protein_annotation_intervals.keys()))}")
        return [self.data[x.data] for x in self.tree.overlap(start, end)]

    def search_pdb_by_id(self, pdb_id):
        try:
            return self.data[pdb_id]
        except KeyError:
            raise KeyError(f"PDB ID {pdb_id} not found. "
                           f"Are you sure this is a COVID-19 protein present in {self.uniprot_id}? "
                           f"Available IDs are {self.data.keys()}")

    def map_to_pdb(self, info_dict):
        pdb_id, chain_id = info_dict["pdb_id"], info_dict["chain_id"]
        pdbe_mapping = self.all_residue_mapping[(pdb_id, chain_id)]
        start, end = int(pdbe_mapping['PDB_BEG']), int(pdbe_mapping['PDB_END'])
        unp_start, unp_end = int(pdbe_mapping["SP_BEG"]), int(pdbe_mapping["SP_END"])
        pdb_alpha = pd.parseCIF(pdb_id, chain=chain_id).select(f"resnum {start} to {end}").select("calpha")
        pdb_sequence_dict = dict(zip(pdb_alpha.getResnums(), pdb_alpha.getSequence()))
        ref_sequence = self.uniprot_sequence[unp_start - 1: unp_end]
        residue_mapping = {}
        mismatches = []
        for i in range(len(ref_sequence)):
            index_1 = i + start
            if index_1 in pdb_sequence_dict:
                if pdb_sequence_dict[index_1] != ref_sequence[i]:
                    mismatches.append((index_1, pdb_sequence_dict[index_1], ref_sequence[i]))
                residue_mapping[index_1] = i + unp_start
        return residue_mapping, mismatches

    def _get_sift_xml(self, pdb_id: str) -> ET.Element:
        ftp_address = "ftp.ebi.ac.uk"
        ftp = ftplib.FTP(ftp_address)
        ftp.login()
        filepath = f"/pub/databases/msd/sifts/split_xml/{pdb_id[1:3]}"
        filename = f"{pdb_id}.xml.gz"
        ftp.cwd(filepath)
        content = list()
        ftp.retrbinary(f"RETR {filename}", content.append)
        ftp.close()
        content = b''.join(content)
        return ET.fromstring(gzip.decompress(content).decode("utf-8"))

    def get_mapping_by_pdb_id(self, pdb_id: str):
        sift_xml = self._get_sift_xml(pdb_id)
        entities = [x for x in sift_xml.iter() if "entity" in x.tag]
        chains = dict()
        for ent in entities:
            chains[ent.attrib["entityId"]] = list()
            for residue in [x for x in ent.iter() if "residue" in x.tag and not x.tag.endswith("Detail")]:
                pdb_resnum = residue.attrib["dbResNum"]
                pdb_resname = residue.attrib["dbResName"]
                try:
                    uniprot_resnum = [x for x in residue.iter() if "dbCoordSys" in x.attrib and x.attrib["dbCoordSys"] == "UniProt"][0].attrib["dbResNum"]
                    chains[ent.attrib["entityId"]].append(dict(pdbResNum=pdb_resnum,
                                                               pdbResName=pdb_resname,
                                                               uniprotResNum=uniprot_resnum))
                except IndexError:
                    continue
        return chains

if __name__ == "__main__":
    mapping = UniProtBasedMapping("P0DTC2")
    mapping.list_available_annotations()
    print(mapping.uniprot_sequence)
    print(len(mapping.uniprot_sequence))
    for x in mapping.search_pdbs_by_protein_name("Spike protein S1"):
        print(x)
    print(mapping.get_mapping_by_pdb_id("6vsb"))
    # mapping.protein_annotation_intervals["3C-like proteinase"]
    # print(mapping.data["6vxx"])
    # print(mapping.search_pdb_by_id("6lu7"))
