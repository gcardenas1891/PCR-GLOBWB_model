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

import .virtualOS as vos

import logging
logger = logging.getLogger(__name__)


class IrrigationWaterDemand(object):

    def __init__(self, iniItems, nameOfSectionInIniFileThatIsRellevantForThisIrrLC, landmask, landCoverObject):
        object.__init__(self)
        
        # make the iniItems for the entire class
        self.iniItems = iniItems
        
        # cloneMap, tmpDir, inputDir based on the configuration/setting given in the ini/configuration file
        self.cloneMap = iniItems.cloneMap
        self.tmpDir   = iniItems.tmpDir
        self.inputDir = iniItems.globalOptions['inputDir']
        self.landmask = landmask
        
        # configuration for this land cover type
        self.iniItemsIrrLC = iniItems.__getattribute__(nameOfSectionInIniFileThatIsRellevantForThisIrrLC)

        # - name of this land cover type
        self.name = self.iniItemsLC['name']
        
        # set the 'static' parameters (mainly soil and topo)
        self.parameters = landCoverObject.parameters

        # height of inundation that is allowed within this land cover 
        self.minTopWaterLayer = landCoverObject.minTopWaterLayer
        
        # crop depletion factor
        self.cropDeplFactor = vos.readPCRmapClone(self.iniItemsIrrLC['cropDeplFactor'], self.cloneMap, \
                                                  self.tmpDir, self.inputDir)
             
        # number of soil layers
        self.numberOfLayers = landCoverObject.numberOfLayers
        
        # root zone depth (m)
        self.maxRootDepth   = landCoverObject.maxRootDepth
        
        # get water capacity within the root zone (z)
        # - this will return self.totAvlWater
        self.calculateTotAvlWaterCapacityInRootZone()
        
        # infiltration/percolation losses for paddy fields
        if self.name == 'irrPaddy' or self.name == 'irr_paddy': self.design_percolation_loss = self.estimate_paddy_infiltration_loss(iniPaddyOptions = self.iniItemsIrrLC)
        
        # irrigation efficiency input (string or file name)
        self.ini_items_for_irrigation_efficiency = None
        if 'irrigationEfficiency' in iniItems.landSurfaceOptions.keys(): self.ini_items_for_irrigation_efficiency = iniItems.landSurfaceOptions['irrigationEfficiency']
        if 'irrigationEfficiency' in self.iniItemsIrrLC.keys(): self.ini_items_for_irrigation_efficiency = iniItems.landSurfaceOptions['irrigationEfficiency']
        if self.ini_items_for_irrigation_efficiency is None:
            logger.info("'irrigationEfficiency' is not defined, we set this to 1.0")
            self.ini_items_for_irrigation_efficiency = "1.0"
        
        
        # TODO: Continue from this!
        
        ini_items_for_irrigation_efficiency = 

        # - if not defined, just set it to to 
        

        
        # - using the one defined in the landSurfaceOptions (if defined there)
        # - using the one defined in the landCoverOptions   (if defined there)


    def get_irrigation_efficiency(self, iniItems, landmask):

        # irrigation efficiency map (in percentage)                     # TODO: Using the time series of efficiency (considering historical technological development).         
        
        # - for the case with pcraster map
        if self.ini_items_for_irrigation_efficiency.endswith(".map"):
            self.irrigationEfficiency = vos.readPCRmapClone(\
                                        self.ini_items_for_irrigation_efficiency,
                                        self.cloneMap, self.tmpDir, self.inputDir)
        # - for the case with netcdf file
        if 'nc' in os.path.splitext(self.ini_items_for_irrigation_efficiency)[1]:
            try:
                # - netCDF file with time dimension
                ncFileIn = vos.getFullPath(self.ini_items_for_irrigation_efficiency, self.inputDir)
                self.irrigationEfficiency = vos.netcdf2PCRobjClone(ncFileIn, "automatic", \
                                                                   currTimeStep, \
                                                                   useDoy = 'yearly',\
                                                                   cloneMapFileName = self.cloneMap)

            except:
                # - netCDF file without time dimension
                msg = "The file " + (ncFileIn) "has no time dimension. Constant values will be used."
                logger.warning(msg)
                self.irrigationEfficiency = vos.readPCRmapClone(\
                                            self.ini_items_for_irrigation_efficiency,
                                            self.cloneMap, self.tmpDir, self.inputDir)
            # TODO: Remove "try" and "except"!                               
        else:
        # - for the case with floating value
             self.irrigationEfficiency = float(self.ini_items_for_irrigation_efficiency)


        extrapolate = True
        if "noParameterExtrapolation" in iniItems.landSurfaceOptions.keys() and iniItems.landSurfaceOptions["noParameterExtrapolation"] == "True": extrapolate = False


        if extrapolate:

             # extrapolate efficiency map:   # TODO: Make a better extrapolation algorithm (considering cell size, etc.). 

             window_size = 1.25 * pcr.clone().cellSize()
             window_size = min(window_size, min(pcr.clone().nrRows(), pcr.clone().nrCols())*pcr.clone().cellSize())
             try:
                 self.irrigationEfficiency = pcr.cover(self.irrigationEfficiency, pcr.windowaverage(self.irrigationEfficiency, window_size))
                 self.irrigationEfficiency = pcr.cover(self.irrigationEfficiency, pcr.windowaverage(self.irrigationEfficiency, window_size))
                 self.irrigationEfficiency = pcr.cover(self.irrigationEfficiency, pcr.windowaverage(self.irrigationEfficiency, window_size))
                 self.irrigationEfficiency = pcr.cover(self.irrigationEfficiency, pcr.windowaverage(self.irrigationEfficiency, window_size))
                 self.irrigationEfficiency = pcr.cover(self.irrigationEfficiency, pcr.windowaverage(self.irrigationEfficiency, window_size))
                 self.irrigationEfficiency = pcr.cover(self.irrigationEfficiency, pcr.windowaverage(self.irrigationEfficiency, 0.75))
                 self.irrigationEfficiency = pcr.cover(self.irrigationEfficiency, pcr.windowaverage(self.irrigationEfficiency, 1.00))
                 self.irrigationEfficiency = pcr.cover(self.irrigationEfficiency, pcr.windowaverage(self.irrigationEfficiency, 1.50))
             except:                                                 
                 pass
        
        #~ self.irrigationEfficiency = pcr.ifthen(self.landmask, self.irrigationEfficiency)
        self.irrigationEfficiency = pcr.cover(self.irrigationEfficiency, 1.0)
        self.irrigationEfficiency = pcr.max(0.1, self.irrigationEfficiency)
        self.irrigationEfficiency = pcr.ifthen(self.landmask, self.irrigationEfficiency)



    def estimate_paddy_infiltration_loss(self, iniPaddyOptions):
        
        # Due to compaction infiltration/percolation loss rate can be much smaller than original soil saturated conductivity
        # - Wada et al. (2014) assume it will be 10 times smaller
        if self.numberOfLayers == 2:\
           design_percolation_loss = self.parameters.kSatUpp/10.           # unit: m/day 
        if self.numberOfLayers == 3:\
           design_percolation_loss = self.parameters.kSatUpp000005/10.     # unit: m/day 

        # However, it can also be much smaller especially in well-puddled paddy fields and should avoid salinization problems.
        # - Default minimum and maximum percolation loss values based on FAO values Reference: http://www.fao.org/docrep/s2022e/s2022e08.htm
        min_percolation_loss = 0.006
        max_percolation_loss = 0.008 
        # - Minimum and maximum percolation loss values given in the ini or configuration file:
        if 'minPercolationLoss' in list(iniPaddyOptions.keys()) and iniPaddyOptions['minPercolationLoss'] != "None":
            min_percolation_loss = vos.readPCRmapClone(iniPaddyOptions['minPercolationLoss'], self.cloneMap,    
                                                       self.tmpDir, self.inputDir)
        if 'maxPercolationLoss' in list(iniPaddyOptions.keys()) and iniPaddyOptions['maxPercolationLoss'] != "None":
            max_percolation_loss = vos.readPCRmapClone(iniPaddyOptions['maxPercolationLoss'], self.cloneMap,    
                                                       self.tmpDir, self.inputDir)
        # - percolation loss at paddy fields (m/day)
        design_percolation_loss = pcr.max(min_percolation_loss, \
                                  pcr.min(max_percolation_loss, design_percolation_loss))
        # - if soil condition is already 'good', we will use its original infiltration/percolation rate
        if self.numberOfLayers == 2:\
           design_percolation_loss = pcr.min(self.parameters.kSatUpp      , design_percolation_loss) 
        if self.numberOfLayers == 3:\
           design_percolation_loss = pcr.min(self.parameters.kSatUpp000005, design_percolation_loss)
        
        # PS: The 'design_percolation_loss' is the maximum loss occuring in paddy fields.
        return design_percolation_loss      


    def calculateTotAvlWaterCapacityInRootZone(self):

        # total water capacity in the root zone (upper soil layers)
        # Note: This is dependent on the land cover type.

        if self.numberOfLayers == 2: 

            self.totAvlWater = \
                               (pcr.max(0.,\
                               self.parameters.effSatAtFieldCapUpp - self.parameters.effSatAtWiltPointUpp))*\
                               (self.parameters.satVolMoistContUpp -   self.parameters.resVolMoistContUpp )*\
                        pcr.min(self.parameters.thickUpp,self.maxRootDepth)  + \
                               (pcr.max(0.,\
                               self.parameters.effSatAtFieldCapLow - self.parameters.effSatAtWiltPointLow))*\
                               (self.parameters.satVolMoistContLow -   self.parameters.resVolMoistContLow )*\
                        pcr.min(self.parameters.thickLow,\
                        pcr.max(self.maxRootDepth-self.parameters.thickUpp,0.))      # Edwin modified this line. Edwin uses soil thickness thickUpp and thickLow (instead of storCapUpp and storCapLow). 
                                                                                     # And Rens support this. 
            self.totAvlWater = pcr.min(self.totAvlWater, \
                            self.parameters.storCapUpp + self.parameters.storCapLow)

        if self.numberOfLayers == 3: 

            self.totAvlWater = \
                               (pcr.max(0.,\
                               self.parameters.effSatAtFieldCapUpp000005 - self.parameters.effSatAtWiltPointUpp000005))*\
                               (self.parameters.satVolMoistContUpp000005 -   self.parameters.resVolMoistContUpp000005 )*\
                        pcr.min(self.parameters.thickUpp000005,self.maxRootDepth)  + \
                               (pcr.max(0.,\
                               self.parameters.effSatAtFieldCapUpp005030 - self.parameters.effSatAtWiltPointUpp005030))*\
                               (self.parameters.satVolMoistContUpp005030 -   self.parameters.resVolMoistContUpp005030 )*\
                        pcr.min(self.parameters.thickUpp005030,\
                        pcr.max(self.maxRootDepth-self.parameters.thickUpp000005))  + \
                               (pcr.max(0.,\
                               self.parameters.effSatAtFieldCapLow030150 - self.parameters.effSatAtWiltPointLow030150))*\
                               (self.parameters.satVolMoistContLow030150 -   self.parameters.resVolMoistContLow030150 )*\
                        pcr.min(self.parameters.thickLow030150,\
                        pcr.max(self.maxRootDepth-self.parameters.thickUpp005030,0.)) 
            #
            self.totAvlWater = pcr.min(self.totAvlWater, \
                               self.parameters.storCapUpp000005 + \
                               self.parameters.storCapUpp005030 + \
                               self.parameters.storCapLow030150)
        
        
                               

    def update(self, meteo, landSurface, groundwater, routing, currTimeStep):
		
        # get variables/values from the landSurface.landCoverObj
        self.cropKC        = landSurface.landCoverObj[self.name].cropKC
        self.topWaterLayer = landSurface.landCoverObj[self.name].topWaterLayer
        self.totalPotET    = landSurface.landCoverObj[self.name].totalPotET
        
        # Contine from this!! get readAvlWater (this is in the function "getSoilStates of landCover.py")
        readAvlWater       
        
        
        # get irrigation efficiency
        # - this will be done on the yearly basis
        if currTimeStep.doy == 1 or currTimeStep.timeStepPCR == 1):
            # - this will return self.irrigationEfficiency
            self.get_irrigation_efficiency(iniItems, landmask, currTimeStep)
		

		# for non paddy and paddy irrigation fields - TODO: to split between paddy and non-paddy fields
        # irrigation water demand (unit: m/day) for paddy and non-paddy
        self.irrGrossDemand = pcr.scalar(0.)
        if (self.name == 'irrPaddy' or self.name == 'irr_paddy'): 
            self.irrGrossDemand = \
                  pcr.ifthenelse(self.cropKC > 0.75, \
                     pcr.max(0.0,self.minTopWaterLayer - \
                                (self.topWaterLayer )), 0.)                # a function of cropKC (evaporation and transpiration),
                                                                           #               topWaterLayer (water available in the irrigation field)
        
        if (self.name == 'irrNonPaddy' or self.name == 'irr_non_paddy' or self.name ==  "irr_non_paddy_crops") and self.includeIrrigation:

            #~ adjDeplFactor = \
                     #~ pcr.max(0.1,\
                     #~ pcr.min(0.8,(self.cropDeplFactor + \
                                  #~ 40.*(0.005-self.totalPotET))))        # from Wada et al. (2014)
            adjDeplFactor = \
                     pcr.max(0.1,\
                     pcr.min(0.8,(self.cropDeplFactor + \
                                  0.04*(5.-self.totalPotET*1000.))))       # original formula based on Allen et al. (1998)
                                                                           # see: http://www.fao.org/docrep/x0490e/x0490e0e.htm#
            #
            #~ # alternative 1: irrigation demand (to fill the entire totAvlWater, maintaining the field capacity) - NOT USED
            #~ self.irrGrossDemand = \
                 #~ pcr.ifthenelse( self.cropKC > 0.20, \
                 #~ pcr.ifthenelse( self.readAvlWater < \
                                  #~ adjDeplFactor*self.totAvlWater, \
                #~ pcr.max(0.0,  self.totAvlWater-self.readAvlWater),0.),0.)  # a function of cropKC and totalPotET (evaporation and transpiration),
                                                                           #~ #               readAvlWater (available water in the root zone)
            
            # alternative 2: irrigation demand (to fill the entire totAvlWater, maintaining the field capacity, 
            #                                   but with the correction of totAvlWater based on the rooting depth)
            # - as the proxy of rooting depth, we use crop coefficient 
            self.irrigation_factor = pcr.ifthenelse(self.cropKC > 0.0,\
                                       pcr.min(1.0, self.cropKC / 1.0), 0.0)
            self.irrGrossDemand = \
                 pcr.ifthenelse( self.cropKC > 0.20, \
                 pcr.ifthenelse( self.readAvlWater < \
                                 adjDeplFactor*self.irrigation_factor*self.totAvlWater, \
                 pcr.max(0.0, self.totAvlWater*self.irrigation_factor-self.readAvlWater),0.),0.)

            # irrigation demand is implemented only if there is deficit in transpiration and/or evaporation
            deficit_factor = 1.00
            evaporationDeficit   = pcr.max(0.0, (self.potBareSoilEvap  + self.potTranspiration)*deficit_factor -\
                                   self.estimateTranspirationAndBareSoilEvap(returnTotalEstimation = True))
            transpirationDeficit = pcr.max(0.0, 
                                   self.potTranspiration*deficit_factor -\
                                   self.estimateTranspirationAndBareSoilEvap(returnTotalEstimation = True, returnTotalTranspirationOnly = True))
            deficit = pcr.max(evaporationDeficit, transpirationDeficit)
            #
            # treshold to initiate irrigation
            deficit_treshold = 0.20 * self.totalPotET
            need_irrigation = pcr.ifthenelse(deficit > deficit_treshold, pcr.boolean(1),\
                              pcr.ifthenelse(self.soilWaterStorage == 0.000, pcr.boolean(1), pcr.boolean(0)))
            need_irrigation = pcr.cover(need_irrigation, pcr.boolean(0.0))
            #
            self.irrGrossDemand = pcr.ifthenelse(need_irrigation, self.irrGrossDemand, 0.0)

            # demand is limited by potential evaporation for the next coming days
            # - objective: to avoid too high and unrealistic demand 
            max_irrigation_interval = 15.0
            min_irrigation_interval =  7.0
            irrigation_interval = pcr.min(max_irrigation_interval, \
                                  pcr.max(min_irrigation_interval, \
                                  pcr.ifthenelse(self.totalPotET > 0.0, \
                                  pcr.roundup((self.irrGrossDemand + pcr.max(self.readAvlWater, self.soilWaterStorage))/ self.totalPotET), 1.0)))
            # - irrigation demand - limited by potential evaporation for the next coming days
            self.irrGrossDemand = pcr.min(pcr.max(0.0,\
                                          self.totalPotET * irrigation_interval - pcr.max(self.readAvlWater, self.soilWaterStorage)),\
                                          self.irrGrossDemand)

            # assume that smart farmers do not irrigate higher than infiltration capacities
            if self.numberOfLayers == 2: self.irrGrossDemand = pcr.min(self.irrGrossDemand, self.parameters.kSatUpp)
            if self.numberOfLayers == 3: self.irrGrossDemand = pcr.min(self.irrGrossDemand, self.parameters.kSatUpp000005)

        # irrigation efficiency, minimum demand for start irrigating and maximum value to cap excessive demand 
        if self.includeIrrigation:

            # irrigation efficiency                                                               # TODO: Improve the concept of irrigation efficiency
            self.irrigationEfficiencyUsed  = pcr.min(1.0, pcr.max(0.10, self.irrigationEfficiency))
            # demand, including its inefficiency
            self.irrGrossDemand = pcr.cover(self.irrGrossDemand / pcr.min(1.0, self.irrigationEfficiencyUsed), 0.0)
            
            # the following irrigation demand is not limited to available water
            self.irrGrossDemand = pcr.ifthen(self.landmask, self.irrGrossDemand)
            
            # reduce irrGrossDemand by netLqWaterToSoil
            self.irrGrossDemand = pcr.max(0.0, self.irrGrossDemand - self.netLqWaterToSoil)
            
            # minimum demand for start irrigating
            minimum_demand = 0.005   # unit: m/day                                                   # TODO: set the minimum demand in the ini/configuration file.
            if self.name == 'irrPaddy' or\
               self.name == 'irr_paddy': minimum_demand = pcr.min(self.minTopWaterLayer, 0.025)      # TODO: set the minimum demand in the ini/configuration file.
            self.irrGrossDemand = pcr.ifthenelse(self.irrGrossDemand > minimum_demand, \
                                                 self.irrGrossDemand , 0.0)                          
                                                                                                     
            maximum_demand = 0.025  # unit: m/day                                                    # TODO: set the maximum demand in the ini/configuration file.  
            if self.name == 'irrPaddy' or\
               self.name == 'irr_paddy': maximum_demand = pcr.min(self.minTopWaterLayer, 0.025)      # TODO: set the minimum demand in the ini/configuration file.
            self.irrGrossDemand = pcr.min(maximum_demand, self.irrGrossDemand)                       
                                                                                                     
            # ignore small irrigation demand (less than 1 mm)                                        
            self.irrGrossDemand = pcr.rounddown( self.irrGrossDemand *1000.)/1000.                   
                                                                                                     
            # irrigation demand is only calculated for areas with fracVegCover > 0                   # DO WE NEED THIS ? 
            self.irrGrossDemand = pcr.ifthenelse(self.fracVegCover >  0.0, self.irrGrossDemand, 0.0)

        # total irrigation gross demand (m) per cover types (not limited by available water)
        self.totalPotentialMaximumIrrGrossDemandPaddy    = 0.0
        self.totalPotentialMaximumIrrGrossDemandNonPaddy = 0.0
        if self.name == 'irrPaddy' or self.name == 'irr_paddy': self.totalPotentialMaximumIrrGrossDemandPaddy = self.irrGrossDemand
        if self.name == 'irrNonPaddy' or self.name == 'irr_non_paddy' or self.name == 'irr_non_paddy_crops': self.totalPotentialMaximumIrrGrossDemandNonPaddy = self.irrGrossDemand

        
