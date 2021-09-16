#!/bin/bash 


set -x


# configuration (.ini) file
INI_FILE=$(pwd)/"setup_05min_ssp370_version_2021-09-16.ini"


# pcrglobwb output folder
MAIN_OUTPUT_DIR="/datadrive/pcrglobwb_output/pcrglobwb_aqueduct_2021/version_2021-09-XX_hist_gfdl-esm4/"


# starting and end dates
STARTING_DATE="1955-01-01"
END_DATE="2014-12-31"


#~ # meteorological forcing files
#~ RELATIVE_HUMIDITY_FORCING_FILE="/datadrive/pcrglobwb_input/data/isimip_forcing/isimip3b_version_2021-05-XX/gfdl-esm4_w5e5_historical_hurs_global_daily_1850_2014.nc"
#~ PRECIPITATION_FORCING_FILE="/datadrive/pcrglobwb_input/data/isimip_forcing/isimip3b_version_2021-05-XX/gfdl-esm4_w5e5_historical_pr_global_daily_1850_2014.nc"
#~ PRESSURE_FORCING_FILE="/datadrive/pcrglobwb_input/data/isimip_forcing/isimip3b_version_2021-05-XX/gfdl-esm4_w5e5_historical_ps_global_daily_1850_2014.nc"
#~ SHORTWAVE_RADIATION_FORCING_FILE="/datadrive/pcrglobwb_input/data/isimip_forcing/isimip3b_version_2021-05-XX/gfdl-esm4_w5e5_historical_rsds_global_daily_1850_2014.nc"
#~ WIND_FORCING_FILE="/datadrive/pcrglobwb_input/data/isimip_forcing/isimip3b_version_2021-05-XX/gfdl-esm4_w5e5_historical_sfcwind_global_daily_1850_2014.nc"
#~ TEMPERATURE_FORCING_FILE="/datadrive/pcrglobwb_input/data/isimip_forcing/isimip3b_version_2021-05-XX/gfdl-esm4_w5e5_historical_tas_global_daily_1850_2014.nc"

# meteorological forcing files - on eejit
RELATIVE_HUMIDITY_FORCING_FILE="/scratch/depfg/sutan101/data/isimip_forcing/isimip3b_version_2021-05-XX/copied_on_2021-06-XX/merged/historical/gfdl-esm4/gfdl-esm4_w5e5_historical_hurs_global_daily_1850_2014.nc"
PRECIPITATION_FORCING_FILE="/scratch/depfg/sutan101/data/isimip_forcing/isimip3b_version_2021-05-XX/copied_on_2021-06-XX/merged/historical/gfdl-esm4/gfdl-esm4_w5e5_historical_pr_global_daily_1850_2014.nc"
PRESSURE_FORCING_FILE="/scratch/depfg/sutan101/data/isimip_forcing/isimip3b_version_2021-05-XX/copied_on_2021-06-XX/merged/historical/gfdl-esm4/gfdl-esm4_w5e5_historical_ps_global_daily_1850_2014.nc"
SHORTWAVE_RADIATION_FORCING_FILE="/scratch/depfg/sutan101/data/isimip_forcing/isimip3b_version_2021-05-XX/copied_on_2021-06-XX/merged/historical/gfdl-esm4/gfdl-esm4_w5e5_historical_rsds_global_daily_1850_2014.nc"
WIND_FORCING_FILE="/scratch/depfg/sutan101/data/isimip_forcing/isimip3b_version_2021-05-XX/copied_on_2021-06-XX/merged/historical/gfdl-esm4/gfdl-esm4_w5e5_historical_sfcwind_global_daily_1850_2014.nc"
TEMPERATURE_FORCING_FILE="/scratch/depfg/sutan101/data/isimip_forcing/isimip3b_version_2021-05-XX/copied_on_2021-06-XX/merged/historical/gfdl-esm4/gfdl-esm4_w5e5_historical_tas_global_daily_1850_2014.nc"


#~ # initial conditions
#~ MAIN_INITIAL_STATE_FOLDER="/datadrive/pcrglobwb_output/pcrglobwb_aqueduct_2021/version_2021-08-17_hist_gfdl-esm4/global/states/"
#~ DATE_FOR_INITIAL_STATES="1979-12-31"

# initial conditions - example on eejit
MAIN_INITIAL_STATE_FOLDER="/scratch/depfg/sutan101/pcrglobwb_aqueduct_2021/version_2021-08-20c_gmd-paper-irrigated-areas/global/states/"
DATE_FOR_INITIAL_STATES="1979-12-31"


# number of spinup years
NUMBER_OF_SPINUP_YEARS="5"


PCRGLOBWB_MODEL_SCRIPT_FOLDER=~/github/edwinkost/PCR-GLOBWB_model_edwin-private-development/model/


# load modules on azure
source activate pcrglobwb_python3


pcrcalc

# - unset pcraster working threads
unset PCRASTER_NR_WORKER_THREADS

# go to the folder that contain PCR-GLOBWB scripts
cd ${PCRGLOBWB_MODEL_SCRIPT_FOLDER}
pwd


# run the model for all clones, from 1 to 53

#~ # - for testing
#~ for i in {2..2}
#~ for i in {2..3}

for i in {1..53}

do

CLONE_CODE=${i}
python3 deterministic_runner_with_arguments.py ${INI_FILE} debug_parallel ${CLONE_CODE} -mod ${MAIN_OUTPUT_DIR} -sd ${STARTING_DATE} -ed ${END_DATE} -pff ${PRECIPITATION_FORCING_FILE} -tff ${TEMPERATURE_FORCING_FILE} -presff ${PRESSURE_FORCING_FILE} -windff ${WIND_FORCING_FILE} -swradff ${SHORTWAVE_RADIATION_FORCING_FILE} -relhumff ${RELATIVE_HUMIDITY_FORCING_FILE} -misd ${MAIN_INITIAL_STATE_FOLDER} -dfis ${DATE_FOR_INITIAL_STATES} -num_of_sp_years ${NUMBER_OF_SPINUP_YEARS} &



done


# merging process
python3 deterministic_runner_merging_with_arguments.py ${INI_FILE} parallel -mod ${MAIN_OUTPUT_DIR} -sd ${STARTING_DATE} -ed ${END_DATE} &


wait

