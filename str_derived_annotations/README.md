# Extract and Visualize Structure-Derived Annotations from PDB Sets

## Library Dependencies

* `numpy`
* `prody`
* `matplotlib`
* `dataclasses`
* `dssp`
* `requests`

## Ensemble Based Output

For a set (ensemble) of related PDB IDs, e.g. the same protein crystallized with different ligands, the following annotations are produced:

* `XXX WHICH FILE IS THIS XXX` : RMSD of each structure to the reference structure (the first PDB ID in list)
* `Average_RMSD.txt`: Average RMSD of each residue across all structures
* `PCA_fluctuations.txt`: Squared fluctuations of each residue according to a PCA across all structures

## Single PDB Based Output

For a single PDB ID, the following annotations are produced. With the exception of solvent accessibility (see description below), elastic network models are utilized. 

* `ENM_fluctuations.txt`: Residue fluctuations
* Perturbation response
  * `Perturbation_Effectiveness.txt`: Effectiveness of each residue in perturbing other residues
  * `Perturbation_Sensitivity.txt`: Sensitivity of each residue to perturbation
* `Mechanical_Stiffness.txt`: Mechanical stiffness
* `Hinge_sites_for_mode_X.txt`: Hinge sites connecting two stretches of structure that may move independently
* `Relative_Solvent_Accesbility.txt`: Relative solvent accessibility

Solvent accessibility utilizes a single PDB and solvent exposed surface area predictions are as produced by [DSSP(https://swift.cmbi.umcn.nl/gv/dssp/DSSP_3.html) and then normalized for each amino acid surface area, based on G-X-G, as reported by [Chothia](https://www.sciencedirect.com/science/article/abs/pii/0022283676901911?via%3Dihub). The atoms used for the solvent calculation include only those selected by the `chain` variable in XXXXX. To analyze only a single monomer or a subset of the structure, select the appropriate chain(s). To select the entire PDB, XXXX.

## Testing the Library

These annotations can be written out as structure annotation and visualized in the beta SWISS-MODEL annotation website (see `example_usage.py` and the annotations folder for examples).

# MLG TODOs

* Test with CHAIN = None
* *dd output file with name of PDB an explanation