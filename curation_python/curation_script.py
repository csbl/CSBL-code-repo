# -*- coding: utf-8 -*-

import cobra
import csv
import time
import os
import argparse

__author__ = "Michal Stolarczyk"
__email__ = "mjs5kd@virginia.edu"
__version__ = "0.9.0"


# define function for binary values to boolean conversion
def to_bool(s):
    return True if s == 1 else False


# define function for path fixing
def fixpath(path):
    return os.path.abspath(os.path.expanduser(path))


# arguments/help definition
if __name__ == "__main__":
    description = '''Model curation script'''
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-m", action="store", dest="model", required=True,
                        help="The path to SBML model file to be curated (in .xml format)")
    parser.add_argument("-d", action="store", dest="delete", required=True,
                        help="The paths(s) to the CSV file(s) with reactions to be deleted from the model.", nargs='*')
    parser.add_argument("-e", action="store", dest="edit", required=True,
                        help="The path(s) to the CSV file(s) with reactions to be edited in the model.", nargs='*')
    parser.add_argument("-a", action="store", dest="added", required=False, default=None,
                        help="The path to the CSV file with added metabolites, their names and formulas.")
    # Argument checking section
    args = parser.parse_args()
    try:
        # check if the model file can be opened, raise error if not
        cobra.io.read_sbml_model(args.model)
    except OSError:
        raise OSError("The SBML file you've provided is invalid or doesn't exist.")
    try:
        # check if the reactions delete file can be opened, raise error if not
        if len(args.delete) == 1:
            open(args.delete[0], 'r')
        else:
            for file in args.delete:
                open(file, 'r')
    except FileNotFoundError:
        raise FileNotFoundError("The file you've provided doesn't exist.")
    try:
        # check if the reactions delete file can be opened, raise error if not
        if len(args.edit) == 1:
            open(args.edit, 'r')
        else:
            for file in args.edit:
                open(file, 'r')
    except FileNotFoundError:
        raise FileNotFoundError("The file you've provided doesn't exist.")
    try:
        # check if the optional metabolites added file can be opened, raise error if not
        if args.added is None:
            pass
        else:
            if len(args.added) == 1:
                open(args.added, 'r')
    except:
        raise FileNotFoundError("The file you've provided doesn't exist.")

# get working directory
dir_path = os.path.dirname(os.path.realpath(__file__))
print("Curation starting in %s" % dir_path)

# read model
original_model = cobra.io.read_sbml_model(args.model)
model = original_model
# get original model parameters for reference
ori_no_of_rxns = len(model.reactions)
ori_no_of_genes = len(model.genes)
ori_obj_val = model.optimize().f

# iterate over the files with reactions to edit
for filename in args.edit:
    # open file
    with open(filename, 'r', encoding='iso-8859-1') as handle:
        file = list(csv.reader(handle))
    # iterate over each line of the file
    for i in range(1, len(file)):
        try:
            # search for the reaction, create new if not present already
            model.reactions.get_by_id(file[i][0])
        except KeyError:
            print('No reaction with ID: %s. Creating...' % (file[i][0]))
        else:
            model.remove_reactions([file[i][0]])
        new_reaction = cobra.Reaction(file[i][0])
        model.add_reactions([new_reaction])
        model.reactions.get_by_id(file[i][0]).build_reaction_from_string(reaction_str=file[i][2])
        model.reactions.get_by_id(file[i][0]).bounds = (float(file[i][8]), float(file[i][9]))
        model.reactions.get_by_id(file[i][0]).reversibility = to_bool(file[i][7])
        model.reactions.get_by_id(file[i][0]).subsystem = file[i][6]
        model.reactions.get_by_id(file[i][0]).gene_reaction_rule = file[i][3]
    del file, handle, filename

# iterate over the file with the reactions to be deleted
for filename in args.delete:
    # open file
    with open(filename, 'r') as handle:
        file = list(csv.reader(handle))
    # iterate over each line of the file
    for i in range(1, len(file)):
        try:
            # search for the reaction, remove if found
            model.reactions.get_by_id(file[i][0])
        except KeyError:
            print('No reaction with ID: %s. Will not be removed' % (file[i][0]))
        else:
            model.remove_reactions([file[i][0]])
    del file, handle, filename

# get current time
timestr = time.strftime("%Y_%m_%d_%H:%M:%S")
filename = fixpath(dir_path + "/output/curated_model_" + timestr)

# save the curated model

cobra.io.write_sbml_model(model, filename + ".xml")

# run if the file with added metabolites was provided
if args.added is not None:
    # read the saved curated file
    new_model = cobra.io.read_sbml_model(filename + ".xml")
    missing_metabolite_names = []
    # get metabolites with missing name attribute
    for met in new_model.metabolites:
        if met.name is None:
            missing_metabolite_names.append(met.id)

    print("\nStarting metabolites attributes curation."
          "\n%d metabolites do not have the name attribute prior to curaton\n" % len(missing_metabolite_names))

    filename = args.added
    # open the optional file with the metabolites attributes
    with open(filename, 'r') as handle:
        file = list(csv.reader(handle))
        for i in range(1, len(file)):
            try:
                # search for the current metabolite in the model, add formula and name if found
                new_model.metabolites.get_by_id(file[i][0])
            except KeyError:
                print('No metabolite with ID: %s. Attributes will not be added' % (file[i][0]))
            else:
                new_model.metabolites.get_by_id(file[i][0]).formula = file[i][2]
                new_model.metabolites.get_by_id(file[i][0]).name = file[i][1]

    # check the results of the metabolites attributes curation
    missing_metabolite_names = []
    for met in new_model.metabolites:
        if met.name is None:
            missing_metabolite_names.append(met.id)

    print("\n%d metabolites do not have the name attribute after curation\n" % len(missing_metabolite_names))
    print(missing_metabolite_names)
    filename = fixpath(dir_path + "/output/curated_model_" + timestr)
    cobra.io.write_sbml_model(new_model, filename + ".xml")

# colors for fancy printing
CGREEN = '\33[92m'
CYELLOW = '\33[33m'
CEND = '\033[0m'
BOLD = '\033[1m'

# print the summary of the curation
print("\n\n\t" + CGREEN + "Curation summary:" + CEND + "\n")

print("\nNumber of genes in original model: %d" % ori_no_of_genes)
print("Number of reactions in original model: %d" % ori_no_of_rxns)
print("Original model growth: %f" % ori_obj_val)

no_of_rxns = len(model.reactions)
no_of_genes = len(model.genes)
model.objective = "biomass"
obj_val = model.optimize().f
print("\nNumber of genes: %d" % no_of_genes)
print("Number of reactions: %d" % no_of_rxns)
print("Curated model growth: %f" % obj_val)

print("\n\n" + CYELLOW + "Curated model saved in: ", filename + ".xml" + CEND + "\n")
