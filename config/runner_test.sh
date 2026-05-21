#!/bin/bash
#SBATCH -N 1
#SBATCH -n 16
#SBATCH -p rome
#SBATCH -t 8:00:00
##SBATCH -J kinematic
#SBATCH -J accutravel
#SBATCH --mail-type=END
#SBATCH --mail-user=gcardenas1891@gmail.com

# load the conda enviroment on Snellius
source activate base
conda activate /gpfs/home6/gcardenas/.conda/envs/geo

# unset pcraster working threads and export the following option 
unset PCRASTER_NR_WORKER_THREADS
export OPENBLAS_NUM_THREADS=1

#python /gpfs/home6/gcardenas/github/qualloc/PCR-GLOBWB_model/model/deterministic_runner.py /gpfs/home6/gcardenas/github/qualloc/PCR-GLOBWB_model/config/setup_05min_2w_Rhine_kinematicwave.ini debug
python /gpfs/home6/gcardenas/github/qualloc/PCR-GLOBWB_model/model/deterministic_runner.py /gpfs/home6/gcardenas/github/qualloc/PCR-GLOBWB_model/config/setup_05min_2w_Rhine_accutraveltime.ini debug
