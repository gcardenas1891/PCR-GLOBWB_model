#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# PCR-GLOBWB (PCRaster Global Water Balance) Global Hydrological Model
#
# Copyright (C) 2016, Edwin H. Sutanudjaja, Rens van Beek, Niko Wanders, Yoshihide Wada, 
# Joyce H. C. Bosmans, Niels Drost, Ruud J. van der Ent, Inge E. M. de Graaf, Jannis M. Hoch, 
# Kor de Jong, Derek Karssenberg, Patricia López López, Stefanie Peßenteiner, Oliver Schmitz, 
# Menno W. Straatsma, Ekkamol Vannametee, Dominik Wisser, and Marc F. P. Bierkens
# Faculty of Geosciences, Utrecht University, Utrecht, The Netherlands
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys

import pcraster as pcr

sys.path.append("..")
import virtualOS as vos

import logging
logger = logging.getLogger(__name__)


class ThermoelectricWaterDemand(object):

    def __init__(self, iniItems, landmask):
        object.__init__(self)
        
        # make the iniItems for the entire class
        self.iniItems = iniItems
        
        # cloneMap, tmpDir, inputDir based on the configuration/setting given in the ini/configuration file
        self.cloneMap = iniItems.cloneMap
        self.tmpDir   = iniItems.tmpDir
        self.inputDir = iniItems.globalOptions['inputDir']
        self.landmask = landmask
        
        # get the file information for thermoelectric water demand (unit: m/day)
        self.thermoelectricWaterDemandOption = False
        if iniItems.waterDemandOptions['includeThermoelectricWaterDemand']  == "True":
            self.thermoelectricWaterDemandOption = True  
            logger.info("Thermoelectric water demand is included in the calculation.")
        else:
            logger.info("Thermoelectric water demand is NOT included in the calculation.")
        
        if self.thermoelectricWaterDemandOption:
            self.thermoelectricWaterDemandFile = \
                vos.getFullPath(\
                    inputPath        = iniItems.waterDemandOptions['thermoelectricWaterDemandFile'], \
                    absolutePath     = self.inputDir, \
                    completeFileName = False)



    def update(self, currTimeStep, read_file = True):

        if read_file:
            self.read_thermoelectric_water_demand_from_files(currTimeStep)
        else:
            self.calculate_thermoelectric_water_demand_for_date(currTimeStep)



    def read_thermoelectric_water_demand_from_files(self, currTimeStep):
        # read thermoelectric water demand
        if currTimeStep.timeStepPCR == 1 or currTimeStep.day == 1:
            if self.thermoelectricWaterDemandOption:
                self.thermoelectricGrossDemand = \
                    pcr.max(0.0, \
                            pcr.cover( \
                                      vos.netcdf2PCRobjClone( \
                                          ncFile           = self.thermoelectricWaterDemandFile, \
                                          varName          = 'thermoelectricGrossDemand', \
                                          dateInput        = currTimeStep.fulldate, \
                                          useDoy           = 'monthly',\
                                          cloneMapFileName = self.cloneMap), \
                                      0.0))
                
                self.thermoelectricNettoDemand = \
                    pcr.max(0.0, \
                            pcr.cover( \
                                      vos.netcdf2PCRobjClone( \
                                          ncFile           = self.thermoelectricWaterDemandFile, \
                                          varName          = 'thermoelectricNettoDemand', \
                                          dateInput        = currTimeStep.fulldate, \
                                          useDoy           = 'monthly', \
                                          cloneMapFileName = self.cloneMap), \
                                      0.0))
                
            else:
                self.thermoelectricGrossDemand = pcr.spatial(pcr.scalar(0.0))
                self.thermoelectricNettoDemand = pcr.spatial(pcr.scalar(0.0))
                logger.debug("Thermoelectric water demand is NOT included.")
            
            # gross and netto industrial water demand in m/day
            self.thermoelectricGrossDemand = pcr.cover(self.thermoelectricGrossDemand, 0.0)
            self.thermoelectricNettoDemand = pcr.cover(self.thermoelectricNettoDemand, 0.0)
            self.thermoelectricNettoDemand = pcr.min(self.thermoelectricGrossDemand, self.thermoelectricNettoDemand)  

            # return flow fraction
            self.thermoelectricReturnFlowFraction = pcr.max(0.0, 1.0 - vos.getValDivZero(self.thermoelectricNettoDemand, self.thermoelectricGrossDemand))



    def calculate_thermoelectric_water_demand_for_date(self, currTimeStep):
        # TODO: We may want to calculate thermoelectric water demand on the fly (read_file = False)
        pass
