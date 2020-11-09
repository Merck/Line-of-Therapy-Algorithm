# This is a script to import csv files that contain special cases used in determining line of therapy

import pandas as pd
from sqlalchemy import create_engine

def cases(indication):

    class Cases():
        def __init__(self, indication = indication):

            # General parameters
            
            par_general = pd.read_csv('reference/' + indication.upper() + '/par_general.csv')
            par_general = par_general[['r_window', 'l_disgap', 'drug_switch_ignore', 'combo_dropped_line_advance']].reset_index(drop = True)
            self.par_general = par_general
            
           # This imports special cases for line name (i.e. If within 28 days 
            # patient switches to EGFR, ALK, PD-1/PD-L1, then regimen is called that)
            line_name = pd.read_csv('reference/' + indication.upper() + '/line_name.csv')
            line_name = line_name[['treatment']].reset_index(drop = True)
            self.line_name = line_name 

            # This imports special cases for drug substitutions/additions that do not advance the line of therapy            
            line_substitutions = pd.read_csv('reference/' + indication.upper() + '/line_substitutions.csv')   
            line_substitutions = line_substitutions[['original', 'substitute']].reset_index(drop = True)
            self.line_substitutions = line_substitutions
            line_additions = pd.read_csv('reference/' + indication.upper() + '/line_additions.csv')    
            #line_additions = line_additions[line_additions['indication'] == indication.upper()].applymap(str.upper)
            line_additions = line_additions[['drug_name']].reset_index(drop = True)
            self.line_additions = line_additions
        
            # This imports special cases for drugs eligible to be considered maintenance therapy
            line_maintenance = pd.read_csv('reference/' + indication.upper() + '/line_maintenance.csv')    
            line_maintenance = line_maintenance[['drug_name', 'maintenance_type']].reset_index(drop = True)
            self.line_maintenance = line_maintenance
        
            # This imports special cases for drugs that are not affected by an episode gap
            episode_gap = pd.read_csv('reference/' + indication.upper() + '/episode_gap.csv')    
            episode_gap = episode_gap[['drug_name']].reset_index(drop = True)
            self.episode_gap = episode_gap

    return(Cases(indication))
