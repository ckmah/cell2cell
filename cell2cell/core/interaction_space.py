# -*- coding: utf-8 -*-

from __future__ import absolute_import

from cell2cell.preprocessing import integrate_data, cutoffs
from cell2cell.core import cell, compute_interaction

import itertools
import numpy as np
import pandas as pd


def generate_interaction_elements(binary_rnaseq, ppi_data, interaction_type, cci_matrix_template=None, verbose=True):
    '''Create all elements of pairwise interactions needed to perform the analyses.
    All these variables are used by the class InteractionSpace.

    Parameters
    ----------



    Returns
    -------
    interaction_space : dict
        Dictionary containing all the pairwise interaction ('pairs' key), cell dictionary ('cells' key) containing all
        cells/tissues/organs with their associated data (rna_seq, binary_ppi, etc) and a Cell-Cell Interaction Matrix
        that scores the possible interaction between each pair of cells ('cci_matrix key) for the respective interaction
        type.
    '''

    if verbose:
        print('Creating ' + interaction_type.capitalize() + ' Interaction Space')

    # Cells
    cell_instances = list(binary_rnaseq.columns)  # @Erick, check if position 0 of columns contain index header.
    cell_number = len(cell_instances)

    # Generate pairwise interactions
    pairwise_interactions = list(itertools.combinations(cell_instances + cell_instances, 2))
    pairwise_interactions = list(set(pairwise_interactions))  # Remove duplicates

    # Interaction elements
    interaction_space = {}
    interaction_space['pairs'] = pairwise_interactions
    interaction_space['cells'] = cell.cells_from_rnaseq(binary_rnaseq, verbose=verbose)

    # Cell-specific binary ppi
    for cell_instance in interaction_space['cells'].values():
        cell_instance.binary_ppi = integrate_data.get_binary_ppi(ppi_data, cell_instance.rnaseq_data, column='value')

    # Cell-cell interaction matrix
    if cci_matrix_template is None:
        interaction_space['cci_matrix'] = pd.DataFrame(np.zeros((cell_number, cell_number)),
                                                       columns=cell_instances,
                                                       index=cell_instances)
    else:
        interaction_space['cci_matrix'] = cci_matrix_template

    return interaction_space


class InteractionSpace():
    '''
    Interaction space that contains all the required elements to perform the analysis between every pair of cells.

    Parameters
    ----------


    Attributes
    ----------


    '''

    def __init__(self, rnaseq_data, ppi_dict, interaction_type, gene_cutoffs, cci_matrix_template=None, verbose=True):
        if 'type' in gene_cutoffs.keys():
            cutoff_values = cutoffs.get_cutoffs(rnaseq_data,
                                                gene_cutoffs,
                                                verbose=verbose)
        else:
            raise ValueError("If dataframe is not included in gene_cutoffs, please provide the type of method to obtain them.")

        self.binary_rnaseq = integrate_data.get_binary_rnaseq(rnaseq_data, cutoff_values)
        self.interaction_type = interaction_type
        self.ppi_data = ppi_dict[self.interaction_type]
        self.interaction_elements = generate_interaction_elements(self.binary_rnaseq,
                                                                  self.ppi_data,
                                                                  self.interaction_type,
                                                                  cci_matrix_template=cci_matrix_template,
                                                                  verbose=verbose)


    def pairwise_interaction(self, cell1, cell2, verbose=True):
        '''
        Function that performs the interaction analysis of a pair of cells.

        Parameters
        ----------
        cell1 : Cell class
            Cell instance generated from RNAseq data.

        cell2 : Cell class
            Cell instance generated from RNAseq data.

        ppi_data: pandas DataFrame object
            DataFrame containing three columns. The first and second ones are for proteins, where each row is an interaction.
            The third column is the 'score' or probability for such interaction. This data should be processed before with 'simplify_ppi'
            in order to reduce the table to the three columns mentioned before.

        product_filter : list or None (default = None)
            List of gene names to consider based on a previous filter with GO terms or any other common pattern. Only those
            genes will be considered and the others excluded.

        Returns
        -------
        cci_score : float
            Score for a the interaction of the specified pair of cells. This score is computed considering all the inter-cell protein-protein
            interactions of the pair of cells.

        interaction_matrix : pandas DataFrame object
            Matrix that contains the respective score for the interaction between a pair of proteins (one protein on cell1
            and the other on cell2).
        '''

        if verbose:
            print("Computing {} interaction between {} and {}".format(self.interaction_type, cell1.type,cell2.type))

        # Calculate cell-cell interaction score
        cci_score = compute_interaction.cci_score_from_binary(cell1, cell2)  # Function to compute cell-cell interaction score
        return cci_score

    def compute_pairwise_interactions(self, verbose=True):
        '''
        Function that computes...

        Parameters
        ----------


        Returns
        -------


        '''
        ### Compute pairwise physical interactions
        if verbose:
            print("Computing pairwise interactions")
        for pair in self.interaction_elements['pairs']:  #@Erick, PARALLELIZE THIS FOR?
            cell1 = self.interaction_elements['cells'][pair[0]]
            cell2 = self.interaction_elements['cells'][pair[1]]
            cci_score = self.pairwise_interaction(cell1, cell2, verbose=verbose)
            self.interaction_elements['cci_matrix'].loc[pair[0], pair[1]] = cci_score
            self.interaction_elements['cci_matrix'].loc[pair[1], pair[0]] = cci_score

    def get_genes_for_filter(self):
        genes = []
        if self.product_filter is not None:
            genes += self.product_filter
        if self.mediators is not None:
            genes += self.mediators
        genes = list(set(genes))
        return genes