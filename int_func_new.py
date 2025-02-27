import logging
from pyscf import gto, scf, ao2mo
from pyscf.lib import param
from scipy import linalg as scila
from pyscf.lib import logger as pylogger
from qiskit_nature import QiskitNatureError
# from qiskit.chemistry import QMolecule
# from qiskit.chemistry import AquaChemistryError
#from qiskit.chemistry import QMolecule

import numpy as np
# import gse_algo as ga
# from qiskit.chemistry import FermionicOperator
#from qiskit.chemistry import FermionicOperator
logger = logging.getLogger(__name__)
from pyscf.scf.hf import get_ovlp


def _calculate_integrals(mol, calc_type='rhf', atomic=False):
    """Function to calculate the one and two electron terms. Perform a Hartree-Fock calculation in
        the given basis.
    Args:
        mol : A PySCF gto.Mole object.
        calc_type: rhf, uhf, rohf
    Returns:
        ehf : Hartree-Fock energy
        enuke : Nuclear repulsion energy
        norbs : Number of orbitals
        mohij : One electron terms of the Hamiltonian.
        mohijkl : Two electron terms of the Hamiltonian.
        mo_coeff: Orbital coefficients
        orbs_energy: Orbitals energies
        x_dip_ints: x dipole moment integrals
        y_dip_ints: y dipole moment integrals
        z_dip_ints: z dipole moment integrals
        nucl_dipl : Nuclear dipole moment
    """
    enuke = gto.mole.energy_nuc(mol)

    if calc_type == 'rhf':
        mf = scf.RHF(mol)
    elif calc_type == 'rohf':
        mf = scf.ROHF(mol)
    elif calc_type == 'uhf':
        mf = scf.UHF(mol)
    else:
        raise QiskitNatureError('Invalid calc_type: {}'.format(calc_type))

    ehf = mf.kernel()

    if type(mf.mo_coeff) is tuple:
        mo_coeff = mf.mo_coeff[0]
        mo_occ   = mf.mo_occ[0]
    else:
        mo_coeff = mf.mo_coeff
        mo_occ   = mf.mo_occ

    norbs = mo_coeff.shape[0]
    orbs_energy = mf.mo_energy
    # print(np.dot(mo_coeff,mo_coeff.T))
    O = get_ovlp(mol)
    # print(np.dot(O,O.T))
    mo_tr = np.dot(np.dot(O,mo_coeff),O.T)

    # print(np.dot(mo_tr,mo_tr.T))

    # two_body_temp = QMolecule.twoe_to_spin(_q_.mo_eri_ints)
    # temp_int = np.einsum('ijkl->ljik', _q_.mo_eri_ints)
    # two_body_temp = QMolecule.twoe_to_spin(temp_int)
    # mol = gto.M(atom=mol.atom, basis='sto-3g')

    # X = np.kron(np.identity(2), np.linalg.inv(scipy.linalg.sqrtm(O)))




    ### for atomic basis
    if atomic:
        mo_coeff = np.identity(len(mo_coeff))
    ###
    # print(mo_coeff)
    hij = mf.get_hcore()
    mohij = np.dot(np.dot(mo_coeff.T, hij), mo_coeff)
    # mohij = hij

    eri = ao2mo.incore.full(mf._eri, mo_coeff, compact=False)
    # eri_1 = mf._eri
    # print(np.shape(eri))
    # print(np.shape(eri_1))
    mohijkl = eri.reshape(norbs, norbs, norbs, norbs)
    
    # exit()


    # dipole integrals
    mol.set_common_orig((0, 0, 0))
    ao_dip = mol.intor_symmetric('int1e_r', comp=3)
    x_dip_ints = QMolecule.oneeints2mo(ao_dip[0], mo_coeff)
    y_dip_ints = QMolecule.oneeints2mo(ao_dip[1], mo_coeff)
    z_dip_ints = QMolecule.oneeints2mo(ao_dip[2], mo_coeff)

    dm = mf.make_rdm1(mf.mo_coeff, mf.mo_occ)
    if calc_type == 'rohf' or calc_type == 'uhf':
        dm = dm[0]
    elec_dip = np.negative(np.einsum('xij,ji->x', ao_dip, dm).real)
    elec_dip = np.round(elec_dip, decimals=8)
    nucl_dip = np.einsum('i,ix->x', mol.atom_charges(), mol.atom_coords())
    nucl_dip = np.round(nucl_dip, decimals=8)
    logger.info("HF Electronic dipole moment: {}".format(elec_dip))
    logger.info("Nuclear dipole moment: {}".format(nucl_dip))
    logger.info("Total dipole moment: {}".format(nucl_dip+elec_dip))

    return ehf, enuke, norbs, mohij, mohijkl, mo_coeff, orbs_energy, x_dip_ints, y_dip_ints, z_dip_ints, nucl_dip
