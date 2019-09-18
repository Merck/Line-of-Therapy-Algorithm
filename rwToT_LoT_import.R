#    Copyright (c) 2019 Merck Sharp & Dohme Corp. a subsidiary of Merck & Co., Inc., Kenilworth, NJ, USA.
#  
#    This file is part of the Line of Therapy Algorithm program.
#
#    Line of Theraphy Algorithm is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

#########################################################################
# rwToT_LoT_import.R - Supporting script containing csv lookup files    #
# Authors: Weilin Meng, Wanmei Ou, Xin Chen, Wynona Black, Qian Xia     #
# Company: Merck (MSD), Center of Observational Research                #
# Date Created: 2018-10-26                                              #
#########################################################################

# This is a script to import csv files that contain special cases used in determining line of therapy

# This imports special cases for line name (i.e. If within 28 days patient switches to EGFR, ALK, PD-1/PD-L1, then regimen is called that)
cases.line_name = sapply(read.csv(paste("reference/",input.indication,"/cases_line_name.csv",sep=''), as.is= TRUE), tolower)

# This imports special cases for drug substitutions/additions that do not advance the line of therapy
cases.line_substitutions = as.data.frame(sapply(read.csv(paste("reference/",input.indication,"/cases_substitutions.csv",sep=''), as.is= TRUE), toupper))
cases.line_additions = sapply(read.csv(paste("reference/",input.indication,"/cases_additions.csv",sep=''), as.is= TRUE), toupper)

# This imports special cases for drugs eligible to be considered maintenance therapy
cases.line_maintenance = sapply(read.csv(paste("reference/",input.indication,"/cases_maintenance.csv",sep=''), as.is= TRUE), toupper)

# This imports special cases for drugs that are not affected by an episode gap
cases.episode_gap = sapply(read.csv(paste("reference/",input.indication,"/cases_episode_gap.csv",sep=''), as.is = TRUE), toupper)