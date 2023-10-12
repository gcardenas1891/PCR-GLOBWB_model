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
        
        # the land cover object (containing land cover model states and parameters)
        self.landCoverObject = landCoverObject
        
        # crop depletion factor
        self.cropDeplFactor = vos.readPCRmapClone(self.iniItemsIrrLC['cropDeplFactor'], self.cloneMap, \
                                                  self.tmpDir, self.inputDir)
             
             
        # infiltration/percolation losses for paddy fields
        if self.name == 'irrPaddy' or self.name == 'irr_paddy': self.design_percolation_loss = self.estimate_paddy_infiltration_loss(self.iniItemsIrrLC, self.landCoverObject)
        


    def get_irrigation_efficiency(self, iniItems, landmask):

        pass



    def estimate_paddy_infiltration_loss(self, iniPaddyOptions, landCoverObject):
        
        # Due to compaction infiltration/percolation loss rate can be much smaller than original soil saturated conductivity
        # - Wada et al. (2014) assume it will be 10 times smaller
        if self.numberOfLayers == 2:\
           design_percolation_loss = self.landCoverObject.parameters.kSatUpp/10.           # unit: m/day 
        if self.numberOfLayers == 3:\
           design_percolation_loss = self.landCoverObject.parameters.kSatUpp000005/10.     # unit: m/day 

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
           design_percolation_loss = pcr.min(self.landCoverObject.parameters.kSatUpp      , design_percolation_loss) 
        if self.numberOfLayers == 3:\
           design_percolation_loss = pcr.min(self.landCoverObject.parameters.kSatUpp000005, design_percolation_loss)
        
        # PS: The 'design_percolation_loss' is the maximum loss occuring in paddy fields.
        return design_percolation_loss      


    def update(self, meteo, landSurface, groundwater, routing, currTimeStep):
		
		# get irrigation efficiency
		self.irrigation_efficiency = self.get_irrigation_efficiency(iniItems, landmask)
		# - TODO: We still have to fill in the function.
		
		# TODO: PLEASE CONTINUE HERE!!!
		
		# for non paddy and paddy irrigation fields - TODO: to split between paddy and non-paddy fields
        # irrigation water demand (unit: m/day) for paddy and non-paddy
        self.irrGrossDemand = pcr.scalar(0.)
        if (self.name == 'irrPaddy' or self.name == 'irr_paddy'):
            self.irrGrossDemand = \
                  pcr.ifthenelse(landSurface.landCoverObj.cropKC > 0.75, \
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

        
