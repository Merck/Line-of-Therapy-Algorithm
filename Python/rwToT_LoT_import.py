# This is a script to import csv files that contain special cases used in determining line of therapy

import pandas as pd

def cases(indication):

    class Cases():
        def __init__(self, indication = indication):

            # This imports special cases for line name (i.e. If within 28 days 
            # patient switches to EGFR, ALK, PD-1/PD-L1, then regimen is called that)
            self.line_name = pd.read_csv("./reference/" + indication + "/cases_line_name.csv").applymap(str.lower)

            # This imports special cases for drug substitutions/additions that do not advance the line of therapy            
            self.line_substitutions = pd.read_csv("./reference/" + indication + "/cases_substitutions.csv").applymap(str.upper)
            self.line_additions = pd.read_csv("./reference/" + indication + "/cases_additions.csv").applymap(str.upper)
        
            # This imports special cases for drugs eligible to be considered maintenance therapy
            self.line_maintenance = pd.read_csv("./reference/" + indication + "/cases_maintenance.csv").applymap(str.upper)
        
            # This imports special cases for drugs that are not affected by an episode gap
            self.episode_gap = pd.read_csv("./reference/" + indication + "/cases_episode_gap.csv").applymap(str.upper)
        
    return(Cases(indication))
