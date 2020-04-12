Extract and visualize structure-derived annotations from (sets of) PDB IDs.

Dependencies
* `numpy`
* `prody`
* `matplotlib`
* `dataclasses`
* `dssp`
* `requests`


For a set of related PDB IDs (e.g. same protein crystallized with different ligands)
* RMSD of each structure to the reference structure (first PDB ID in list)
* Average RMSD of each residue across all structures
* Squared fluctuations of each residue according to a PCA across all structures

For a single PDB ID, predict the following. With the exception of solvent accessibility, elastic network models are utilized. The solvent accessibility utilizes DSSP. Note that the solvent accessibility will include only the selected atoms in the calculation.

* Residue fluctuations
* Perturbation response
  * Effectiveness of each residue in perturbing other residues
  * Sensitivity of each residue to perturbation
* Mechanical stiffness
* Hinge sites connecting two stretches of structure that may move independently
* Relative solvent accessibility

These annotations can be written out as structure annotation and visualized in the beta SWISS-MODEL annotation website (see `example_usage.py` and the annotations folder for examples).
