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


class WaterManagement(object):

    def __init__(self, iniItems, landmask):
        object.__init__(self)

        # make iniItems available for other modules/ functions
        self.iniItems = iniItems
        
        # cloneMap, tmpDir, inputDir based on the configuration/setting given in the ini/configuration file
        self.cloneMap = iniItems.cloneMap
        self.tmpDir   = iniItems.tmpDir
        self.inputDir = iniItems.globalOptions['inputDir']
        self.landmask = landmask
        
        
        # option to prioritize local sources before abstracting water from neighboring cells
        self.prioritizeLocalSourceToMeetWaterDemand = True
        
        # option to prioritize surface water (at this moment, this is always False)
        self.surfaceWaterPiority = False
        
        # cell area (unit: m2)
        cellArea = vos.readPCRmapClone(\
          iniItems.routingOptions['cellAreaMap'],
          self.cloneMap,self.tmpDir,self.inputDir)
        self.cellArea = pcr.ifthen(self.landmask, cellArea)

        # desalination water supply option
        self.includeDesalination = False
        if iniItems.landSurfaceOptions['desalinationWater'] not in ["None", "False"]:
            logger.info("Monthly desalination water use is included.")
            self.includeDesalination = True
            self.desalinationWaterFile = vos.getFullPath(iniItems.landSurfaceOptions['desalinationWater'], self.inputDir)
        else:    
            logger.info("Monthly desalination water is NOT included.")

        
        # zonal IDs at which allocations of desalined water, surface water, and groundwater sources are performed  
        # - if not defined, only local cell water availability is considered
        self.usingAllocationSegmentsForDesalinatedWaterSource = False
        self.usingAllocationSegmentsForSurfaceWaterSource     = False
        self.usingAllocationSegmentsForGroundwaterSource      = False
        sources = ["allocationSegmentsForDesalinatedWaterSource",
                   "allocationSegmentsForSurfaceWaterSource    ",
                   "allocationSegmentsForGroundwaterSource     "]
        for source in sources:
            if ((source in iniItems.waterManagementOptions.keys()) and (iniItems.waterManagementOptions[source] not in ["False", "None"])):
                vars(self)[var], vars(self)[var+"Areas"] = get_allocation_zone(iniItems.waterManagementOptions[source])
            else:
                vars(self)[var], vars(self)[var+"Areas"] = None, None


        source_names = ["desalinated_water", "surface_water", "renewable_groundwater", "nonrenewable_groundwater"]
        sector_names = ["domestic", "industry", "manufacture", "thermoelectric", "livestock", "irrigation"]   
        
        ['irrigation','domestic','industry','livestock']
        
        
        # instantiate the following variable: 
        # - allocated_withdrawal_per_sector[source_name][sector_name]: the amount of water taken from the "source_name" to the "sector_name" 
        # - note that this from the point of view of pixels which are source
        self.allocated_withdrawal_per_sector = {}
        for source_name in source_names: 
            self.allocated_withdrawal_per_sector[source_name] = {}
            for sector_name in sector_names:
                self.allocated_withdrawal_per_sector[source_name][sector_name] = None

        # instantiate the following variable: 
        # - self.allocated_demand_per_sector[source_name][sector_name]: the amount of water given to the "sector_name" from the "source"
        # - note that this from the point of view of pixels that have demands 
        self.allocated_demand_per_sector = {}
        for source_name in source_names: 
            self.allocated_demand_per_sector[source_name] = {}
            for sector_name in sector_names:
                self.allocated_demand_per_sector[source_name][sector_name] = None

        # instantiate the following variable: 
        # - self.met_demand_per_sector[sector_name]: the amount of demand that has been met for every "sector_name"
        # - note that this from the point of view of pixels that have demands 
        # - this is actually the sum of "allocated_demand_per_sector"
        self.met_demand_per_sector = {}
        for sector_name in sector_names:
            self.met_demand_per_sector[sector_name] = None
        

        # ~ # instantiate the following variable: - THIS MAY NOT BE NEEDED
        # ~ # - self.remaining_demand_per_sector[sector_name]: the amount of demand that has NOT been met for every "sector_name"
        # ~ # - note that this from the point of view of pixels that have demands 
        # ~ self.remaining_demand_per_sector = {}
        # ~ for sector_name in sector_names:
            # ~ self.remaining_demand_per_sector[sector_name] = None



    def get_allocation_zone(zonal_map_file_name)

        allocSegments = vos.readPCRmapClone(zonal_map_file_name,
         self.cloneMap, self.tmpDir, self.inputDir, isLddMap=False, cover=None, isNomMap=True)
        allocSegments = pcr.ifthen(self.landmask, allocSegments)
        allocSegments = pcr.clump(allocSegments)
        
        extrapolate = True
        if "noParameterExtrapolation" in self.iniItems.waterManagementOptions.keys() and self.iniItems.waterManagementOptions["noParameterExtrapolation"] == "True": extrapolate = False

        if extrapolate:
            # extrapolate it to half degree resolution
            allocSegments = pcr.cover(allocSegments, \
                                      pcr.windowmajority(allocSegments, 0.5))

        allocSegments = pcr.ifthen(self.landmask, allocSegments)
        
        # clump it and cover the rests with cell ids 
        allocSegments = pcr.clump(allocSegments)
        cell_ids = pcr.mapmaximum(pcr.scalar(allocSegments)) + pcr.scalar(100.0) + pcr.uniqueid(pcr.boolean(1.0))
        allocSegments = pcr.cover(allocSegments, pcr.nominal(cell_ids))                               
        allocSegments = pcr.clump(allocSegments)
        allocSegments = pcr.ifthen(self.landmask, allocSegments)

        # zonal/segment area (unit: m2)
        segmentAreas = pcr.areatotal(pcr.cover(self.cellArea, 0.0), allocSegments)
        segmentAreas = pcr.ifthen(self.landmask, segmentAreas)
        
        return allocSegments, segmentAreas  



    def waterAbstractionAndAllocation(water_demand_volume,
                                      available_water_volume, 
                                      allocation_zones,
                                      zone_area = None,
                                      high_volume_treshold = None,
                                      debug_water_balance = True,\
                                      extra_info_for_water_balance_reporting = "",
                                      landmask = None,
                                      ignore_small_values = False,
                                      prioritizing_local_source = True):
    
       logger.debug("Allocation of abstraction.")
       
       if landmask is not None:
           water_demand_volume = pcr.ifthen(landmask, pcr.cover(water_demand_volume, 0.0))
           available_water_volume = pcr.ifthen(landmask, pcr.cover(available_water_volume, 0.0))
           allocation_zones = pcr.ifthen(landmask, allocation_zones)
       
       # satistify demand with local sources:
       localAllocation  = pcr.scalar(0.0)
       localAbstraction = pcr.scalar(0.0)
       cellVolDemand = pcr.max(0.0, water_demand_volume)
       cellAvlWater  = pcr.max(0.0, available_water_volume)
       if prioritizing_local_source:
           logger.debug("Allocation of abstraction - first, satisfy demand with local source.")
       
           # demand volume in each cell (unit: m3)
           if landmask is not None:
               cellVolDemand = pcr.ifthen(landmask, pcr.cover(cellVolDemand, 0.0))
           
           # total available water volume in each cell
           if landmask is not None:
               cellAvlWater = pcr.ifthen(landmask, pcr.cover(cellAvlWater, 0.0))
           
           # first, satisfy demand with local source
           localAllocation  = pcr.max(0.0, pcr.min(cellVolDemand, cellAvlWater))
           localAbstraction = localAllocation * 1.0
       
       logger.debug("Allocation of abstraction - satisfy demand with neighbour sources.")
       
       # the remaining demand and available water
       cellVolDemand = pcr.max(0.0, cellVolDemand - localAllocation ) 
       cellAvlWater  = pcr.max(0.0, cellAvlWater  - localAbstraction)
       
       # ignoring small values of water availability
       if ignore_small_values: available_water_volume = pcr.max(0.0, pcr.rounddown(available_water_volume))
       
       # demand volume in each cell (unit: m3)
       cellVolDemand = pcr.max(0.0, cellVolDemand)
       if landmask is not None:
           cellVolDemand = pcr.ifthen(landmask, pcr.cover(cellVolDemand, 0.0))
       
       # total demand volume in each zone/segment (unit: m3)
       zoneVolDemand = pcr.areatotal(cellVolDemand, allocation_zones)
       
       # avoid very high values of available water
       cellAvlWater  = pcr.min(cellAvlWater, zoneVolDemand)
       
       # total available water volume in each cell
       cellAvlWater  = pcr.max(0.0, cellAvlWater)
       if landmask is not None:
           cellAvlWater = pcr.ifthen(landmask, pcr.cover(cellAvlWater, 0.0))
       
       # total available water volume in each zone/segment (unit: m3)
       zoneAvlWater  = pcr.areatotal(cellAvlWater, allocation_zones)
       
       # total actual water abstraction volume in each zone/segment (unit: m3)
       # - limited to available water
       zoneAbstraction = pcr.min(zoneAvlWater, zoneVolDemand)
       
       # actual water abstraction volume in each cell (unit: m3)
       cellAbstraction = getValDivZero(\
                         cellAvlWater, zoneAvlWater, smallNumber) * zoneAbstraction
       cellAbstraction = pcr.min(cellAbstraction, cellAvlWater)                                                                   
       
       # to minimize numerical errors
       if high_volume_treshold is not None:
           # mask: 0 for small volumes ; 1 for large volumes (e.g. lakes and reservoirs)
           mask = pcr.cover(\
                  pcr.ifthen(cellAbstraction > high_volume_treshold, pcr.boolean(1)), pcr.boolean(0))
           zoneAbstraction  = pcr.areatotal(
                              pcr.ifthenelse(mask, 0.0, cellAbstraction), allocation_zones)
           zoneAbstraction += pcr.areatotal(                
                              pcr.ifthenelse(mask, cellAbstraction, 0.0), allocation_zones)
       
       # allocation water to meet water demand (unit: m3)
       cellAllocation  = getValDivZero(\
                         cellVolDemand, zoneVolDemand, smallNumber) * zoneAbstraction 
       cellAllocation  = pcr.min(cellAllocation,  cellVolDemand)
       
       # adding local abstraction and local allocation
       cellAbstraction = cellAbstraction + localAbstraction
       cellAllocation  = cellAllocation  + localAllocation
       
       if debug_water_balance and zone_area is not None:
       
           waterBalanceCheck([pcr.cover(pcr.areatotal(cellAbstraction, allocation_zones)/zone_area, 0.0)],\
                             [pcr.cover(pcr.areatotal(cellAllocation , allocation_zones)/zone_area, 0.0)],\
                             [pcr.scalar(0.0)],\
                             [pcr.scalar(0.0)],\
                             'abstraction - allocation per zone/segment (PS: Error here may be caused by rounding error.)' ,\
                              True,\
                              extra_info_for_water_balance_reporting,threshold=1e-4)
       
       return cellAbstraction, cellAllocation, zoneAbstraction

    def update(self, vol_gross_sectoral_water_demands, groundwater, routing, currTimeStep):

        # initiate the variables for remaining sectoral water demands and accumulated variables for sectoral water demands that have been satisfied
        # - both have the unit m3
        self.accumulated_satisfied_gross_sectoral_water_demands = {}
        self.remaining_gross_sectoral_water_demands = {}
        for sector_name in self.gross_sectoral_water_demands.keys():
             self.satisfied_gross_sectoral_water_demands[sector_name] = pcr.scalar(0.0) 
			 self.remaining_gross_sectoral_water_demands[sector_name] = vol_gross_sectoral_water_demands[sector_name]
        
        # initiate the variables for remaining volumes of surface water, as well as renewable and non renewable groundwater
        # - all in volume units (m3)
        self.available_surface_water_volume     = routing.readAvlChannelStorage
        self.available_renewable_groundwater    = groundwater.storGroundwater       * self.cellArea
        self.available_nonrenewable_groundwater = groundwater.storGroundwaterFossil * self.cellArea 
        
        # abstract and allocate desalinated water
        # - this will return the following:
        #   - self.allocated_demand_per_sector["desalinated_water"]
        #   - self.allocated_withdrawal_per_sector["desalinated_water"]
        self.abstraction_and_allocation_from_desalination(self.remaining_gross_sectoral_water_demands)
        
        # update the following after abstraction and allocation of desalinated water
        #   - the updated self.remaining_gross_sectoral_water_demands (after desalinated_water use)
        #   - the updated self.satisfied_gross_sectoral_water_demands (after desalinated_water use)
        for sector_name in self.gross_sectoral_water_demands.keys():
             self.satisfied_gross_sectoral_water_demands[sector_name] += self.allocated_demand_per_sector["desalinated_water"][sector_name]  
			 self.remaining_gross_sectoral_water_demands[sector_name] -= self.allocated_demand_per_sector["desalinated_water"][sector_name]
			 self.remaining_gross_sectoral_water_demands[sector_name]  = pcr.max(0.0, self.remaining_gross_sectoral_water_demands[sector_name])
        
        
        # abstract and allocate surface water
        # - this will return the following:
        #   - self.allocated_demand_per_sector["surface_water"]
        #   - self.allocated_withdrawal_per_sector["surface_water"]
        self.abstraction_and_allocation_from_surface_water(remaining_gross_sectoral_water_demands = self.remaining_gross_sectoral_water_demands, \
                                                           available_surface_water_volume         = self.available_surface_water_volume, \
                                                           routing                                = routing, \
                                                           groundwater                            = groundwater)

        # update the following after abstraction and allocation of surface water
        #   - the updated self.remaining_gross_sectoral_water_demands
        #   - the updated self.satisfied_gross_sectoral_water_demands
        for sector_name in self.gross_sectoral_water_demands.keys():
             self.satisfied_gross_sectoral_water_demands[sector_name] += self.allocated_demand_per_sector["surface_water"][sector_name]  
			 self.remaining_gross_sectoral_water_demands[sector_name] -= self.allocated_demand_per_sector["surface_water"][sector_name]
			 self.remaining_gross_sectoral_water_demands[sector_name]  = pcr.max(0.0, self.remaining_gross_sectoral_water_demands[sector_name])



        # abstract and allocate groundwater
        # - this will return the following:
        #   - self.allocated_demand_per_sector["renewable_groundwater"]
        #   - self.allocated_withdrawal_per_sector["renewable_groundwater"]
        #   - self.allocated_demand_per_sector["nonrenewable_groundwater"]
        #   - self.allocated_withdrawal_per_sector["nonrenewable_groundwater"]
        self.abstraction_and_allocation_from_groundwater(remaining_gross_sectoral_water_demands = self.remaining_gross_sectoral_water_demands,\
                                                         routing                                = routing,\
                                                         groundwater                            = groundwater)


        #   - the updated self.available_renewable_groundwater   
        #   - the updated self.available_nonrenewable_groundwater


    def allocate_satisfied_demand_to_each_sector(totalVolWaterAllocation, sectoral_remaining_demand_volume, total_remaining_demand_volume):

        allocated_demand_per_sector = {}
        for sector_name in self.sector_names:
            allocated_demand_per_sector[sector_name] = vos.getValDivZero(sectoral_remaining_demand_volume[sector_name], total_remaining_demand_volume) * totalVolWaterAllocation
            
        return allocated_demand_per_sector    


    def allocate_withdrawal_to_each_sector(self, totalVoCellWaterAbsraction, totalVolZoneAbstraction, cellAllocatedDemandPerSector, allocation_zones = None):

        # for the case without allocation zone
        allocated_withdrawal_per_sector = cellAlllocatedDemandPerSector

        # for the case with allocation zone
        if allocation_zones is not None:
            zonal_allocated_withdrawal_per_sector = {}
            for sector_name in sector_names:
                zonal_allocated_withdrawal_per_sector[sector_name] = pcr.areatotal(cellAlllocatedDemandPerSector[sector_name], allocation_zones)   
                allocated_withdrawal_per_sector[sector_name] = totalVolCellWaterAbsraction * vos.getValDivZero(zonal_allocated_withdrawal_per_sector[sector_name], totalVolZoneAbstraction)
        
        return allocated_withdrawal_per_sector    



    def abstraction_and_allocation_from_desalination(remaining_gross_sectoral_water_demands):

        # get the TOTAL (remaining) demand (m3) 
        volTotalRemainingDemand = pcr.scalar(0.0) 
        for sector_name in remaining_gross_sectoral_water_demands.keys():
             volTotalRemainingDemand = volTotalRemainingDemand + remaining_gross_sectoral_water_demands[sector_name]


         # get desalination water use (m/day); assume this one as potential supply
        if self.includeDesalination: 
            logger.debug("Monthly desalination water use is included.")
            if (currTimeStep.timeStepPCR == 1 or currTimeStep.day == 1):
                desalinationWaterUse = \
                     pcr.ifthen(self.landmask,\
                     pcr.cover(\
                     vos.netcdf2PCRobjClone(self.desalinationWaterFile,'desalination_water_use',\
                         currTimeStep.fulldate, useDoy = 'monthly', cloneMapFileName = self.cloneMap), 0.0))
                self.desalinationWaterUse = pcr.max(0.0, desalinationWaterUse)
        else:    
            logger.debug("Monthly desalination water use is NOT included.")
            self.desalinationWaterUse = pcr.scalar(0.0)
        # - convert it to volume (m3)
        volDesalinationWaterUse = pcr.max(0.0, self.desalinationWaterUse * self.cellArea)    

        
        # Abstraction and Allocation of DESALINATED WATER
        # ##################################################################################################################
        # - desalination water to satisfy water demand
        if self.usingAllocationSegmentsForDesalinatedWaterSource:
        #  
            logger.debug("Allocation of supply from desalination water.")
        #  
            volDesalinationAbstraction, volDesalinationAllocation, volZoneDesalinationAbstraction = \
              waterAbstractionAndAllocation(
              water_demand_volume = volTotalRemainingDemand,\
              available_water_volume = volDesalinationWaterUse,\
              allocation_zones = self.allocationSegmentsForDesalinatedWaterSource,\
              zone_area = self.allocationSegmentsForDesalinatedWaterSourceAreas,\
              high_volume_treshold = None,\
              debug_water_balance = True,\
              extra_info_for_water_balance_reporting = str(currTimeStep.fulldate), 
              landmask = self.landmask,
              ignore_small_values = False,
              prioritizing_local_source = self.prioritizeLocalSourceToMeetWaterDemand)
        #     
        else: 
        #     
            logger.debug("Supply from desalination water is only for satisfying local demand (no network).")
            volDesalinationAbstraction      = pcr.min(volDesalinationWaterUse, volTotalRemainingDemand)
            volDesalinationAllocation       = volDesalinationAbstraction
            volZoneDesalinationAbstraction  = volDesalinationAbstraction
        # ##################################################################################################################
        # - end of Abstraction and Allocation of DESALINATED WATER


        # allocate the "desalination Allocation" to each sector - unit: m3
        self.allocated_demand_per_sector["desalinated_water"] = self.allocate_satisfied_demand_to_each_sector(totalVolWaterAllocation = volDesalinationAllocation, sectoral_remaining_demand_volume = remaining_gross_sectoral_water_demands, total_remaining_demand_volume = volTotalRemainingDemand)


        # allocate the "desalination Abastraction" to each sector - unit: m3
        self.allocated_withdrawal_per_sector["desalinated_water"] = self.allocate_withdrawal_to_each_source(totalVolCellWaterAbstraction = volDesalinationAbstraction, totalVolZoneAbstraction = volZoneDesalinationAbstraction, cellAllocatedDemandPerSector = self.allocated_demand_per_sector["desalinated_water", allocation_zones = self.allocationSegmentsForDesalinatedWaterSource)
        
        
        # remaining desalination water use - unit: m3
        self.volRemainingDesalinationWaterUse = pcr.max(0.0, volDesalinationWaterUse - volDesalinationAbstraction)
        

                                                     

    def abstraction_and_allocation_from_surface_water(self, \
                                                            remaining_gross_sectoral_water_demands,\
                                                            available_surface_water_volume,\        
                                                            routing,\                                
                                                            groundwater\
                                                            ):


        # Abstraction and Allocation of SURFACE WATER
        ##############################################################################################################################
        # calculate the estimate of surface water demand (considering by swAbstractionFractionDict)
        
        # - get a dictionary containing the partitioning of withdrawal/abstraction sources: (from groundwater and surface water)
        swAbstractionFractionDict = self.partitioningGroundSurfaceAbstraction(routing.avgDischarge, routing.avgBaseflow)
        
        # - surface water abstraction fraction for industrial and domestic (as well as manufacture and thermoelectic, excluding irrigation and livestock)
        swAbstractionFraction_industrial_domestic = pcr.min(swAbstractionFractionDict['max_for_non_irrigation'],\
                                                            swAbstractionFractionDict['estimate'])
        if swAbstractionFractionDict['non_irrigation'] is not None:
            swAbstractionFraction_industrial_domestic = swAbstractionFractionDict['non_irrigation']

        # calculate the remaining demands for the following combined sectors - NOTE THAT they are in VOLUME (m3/day)
        remainingIndustrialDomestic   = pcr.scalar(0.0)
        remainingIrrigationLivestock  = pcr.scalar(0.0)
        for sector_name in remaining_gross_sectoral_water_demands.keys():
            if sector_name != "irrigation" or sector_name != "livestock":
                remainingIndustrialDomestic  += remaining_gross_sectoral_water_demands[sector_name]
            else:
                remainingIrrigationLivestock += remaining_gross_sectoral_water_demands[sector_name]
        # - total remaining demand, from all sectors
        remainingTotalDemand = remainingIndustrialDomestic + remainingIndustrialDomestic        
       
        # TODO: Continue from this!!!
        
        # - surface water demand estimate (so far, only from sectors outside irrigation and livestock) 
        surface_water_demand_estimate = swAbstractionFraction_industrial_domestic * remainingIndustrialDomestic
        
        # - for irrigation and livestock 
        surface_water_irrigation_demand_estimate = swAbstractionFractionDict['irrigation'] * remainingIrrigationLivestock

        # - surface water source as priority if groundwater irrigation fraction is relatively low  
        surface_water_irrigation_demand_estimate = \
           pcr.ifthenelse(swAbstractionFractionDict['irrigation'] >= swAbstractionFractionDict['treshold_to_maximize_irrigation_surface_water'],\
           remainingIrrigationLivestock, surface_water_irrigation_demand_estimate)

        # - update estimate of surface water demand withdrawal (unit: m3/day)
        surface_water_demand_estimate += surface_water_irrigation_demand_estimate

        # - prioritize surface water use in non productive aquifers that have limited groundwater supply
        surface_water_demand_estimate = pcr.ifthenelse(groundwater.productive_aquifer, surface_water_demand_estimate,\
                                                       pcr.max(0.0, remainingIrrigationLivestock - \
                                                       pcr.min(groundwater.avgAllocationShort * self.cellArea, groundwater.avgAllocation * self.cellArea)))
        # - maximize/optimize surface water use in areas with the overestimation of groundwater supply 
        surface_water_demand_estimate += pcr.max(0.0, pcr.max(groundwater.avgAllocationShort  * self.cellArea, groundwater.avgAllocation * self.cellArea) -\
               (1.0 - swAbstractionFractionDict['irrigation']) * remainingIrrigationLivestock -\
               (1.0 - swAbstractionFraction_industrial_domestic) * (remainingIndustrialDomestic))
        #
        # total demand (unit3: m/day) that should be allocated from surface water 
        # (corrected/limited by swAbstractionFractionDict and limited by the remaining demand)
        surface_water_demand_estimate         = pcr.min(remainingTotalDemand, surface_water_demand_estimate)
        correctedRemainingIrrigationLivestock = pcr.min(surface_water_demand_estimate, remainingIrrigationLivestock)
        correctedRemainingIndustrialDomestic  = pcr.min(remainingIndustrialDomestic,\
                                                pcr.max(0.0, surface_water_demand_estimate - remainingIrrigationLivestock))
        correctedSurfaceWaterDemandEstimate   = correctedRemainingIrrigationLivestock + correctedRemainingIndustrialDomestic
        surface_water_demand = correctedSurfaceWaterDemandEstimate
        #
        # if surface water abstraction as the first priority
        if self.surfaceWaterPiority: surface_water_demand = remainingTotalDemand
        

        # TODO: Incorporate the "environmental flow" concept of Rens. This may affect the estimate of 'surface_water_demand'.


        # Abstraction and Allocation of SURFACE WATER
        # ##################################################################################################################
        # - surface water to satisfy water demand
        if self.usingAllocationSegmentsForSurfaceWaterSource:
        #  
            logger.debug("Allocation of supply from surfacen water.")
        #  
            volSurfaceWaterAbstraction, volSurfaceWaterAllocation, volZoneSurfaceWaterAbstraction = \
              waterAbstractionAndAllocation(
              water_demand_volume = surface_water_demand,\
              available_water_volume = available_surface_water_volume,\
              allocation_zones = self.allocationSegmentsForSurfaceWaterSource,\
              zone_area = self.allocationSegmentsForSurfaceWaterSourceAreas,\
              high_volume_treshold = None,\
              debug_water_balance = True,\
              extra_info_for_water_balance_reporting = str(currTimeStep.fulldate), 
              landmask = self.landmask,
              ignore_small_values = False,
              prioritizing_local_source = self.prioritizeLocalSourceToMeetWaterDemand)
        #     
        else: 
        #     
            logger.debug("Supply from surface water is only for satisfying local demand (no network).")
            volSurfaceWaterAbstraction      = pcr.min(available_surface_water_volume, surface_water_demand)
            volSurfaceWaterAllocation       = volSurfaceWaterAbstraction
            volZoneSurfaceWaterAbstraction  = volSurfaceWaterAbstraction
        # ##################################################################################################################
        # - end of Abstraction and Allocation of SURFACE WATER


        # allocate the "surface water Allocation" to each sector - unit: m3
        self.allocated_demand_per_sector["surface_water"] = self.allocate_satisfied_demand_to_each_sector(totalVolWaterAllocation = volSurfaceWaterAllocation, sectoral_remaining_demand_volume = remaining_gross_sectoral_water_demands, total_remaining_demand_volume = remainingTotalDemand)


        # allocate the "surface water Abastraction" to each sector - unit: m3
        self.allocated_withdrawal_per_sector["surface_water"] = self.allocate_withdrawal_to_each_source(totalVolCellWaterAbstraction = volSurfaceWaterAbstraction, totalVolZoneAbstraction = volZoneSurfaceWaterAbstraction, cellAllocatedDemandPerSector = self.allocated_demand_per_sector["surface_water"], allocation_zones = self.allocationSegmentsForSurfaceWaterSource)
        
        
        # remaining surface water that can be extracted - unit: m3
        self.volRemainingSurfaceWater = pcr.max(0.0,  available_surface_water_volume - volSurfaceWaterAbstraction)
        

        # pass the estimates in swAbstractionFractionDict for other modules
        self.swAbstractionFractionDict = swAbstractionFractionDict



    def abstraction_and_allocation_from_groundwater(remaining_gross_sectoral_water_demands, routing, groundwater):
        
        # ~ self.abstraction_and_allocation_from_renewable_groundwater(remaining_gross_sectoral_water_demands, groundwater)
        # ~ self.abstraction_and_allocation_from_non_renewable_groundwater(remaining_gross_sectoral_water_demands, groundwater)
        
        
        # calculate the remaining demands for the following combined sectors - NOTE THAT they are in VOLUME (m3/day)
        remainingIndustrialDomestic   = pcr.scalar(0.0)
        remainingIrrigationLivestock  = pcr.scalar(0.0)
        for sector_name in remaining_gross_sectoral_water_demands.keys():
            if sector_name != "irrigation" or sector_name != "livestock":
                remainingIndustrialDomestic  += remaining_gross_sectoral_water_demands[sector_name]
            else:
                remainingIrrigationLivestock += remaining_gross_sectoral_water_demands[sector_name]
        # - total remaining demand, from all sectors
        remainingTotalDemand = remainingIndustrialDomestic + remainingIndustrialDomestic        
        

        # Abstraction and Allocation of GROUNDWATER (fossil and non fossil)
        #########################################################################################################################
        # estimating groundwater water demand:
        # - demand for industrial and domestic sectors 
        #   (all remaining demand for these sectors should be satisfied)
        groundwater_demand_estimate = remainingIndustrialDomestic
        # - demand for irrigation and livestock sectors
        #   (only part of them will be satisfied, as they may be too high due to the uncertainty in the irrigation scheme)
        irrigationLivestockGroundwaterDemand = pcr.min(remainingIrrigationLivestock, \
                                               pcr.max(0.0, \
                                               (1.0 - self.swAbstractionFractionDict['irrigation']) * remainingIrrigationLivestock))
        groundwater_demand_estimate += irrigationLivestockGroundwaterDemand


        #############################################################################################################################
        # water demand that must be satisfied by groundwater abstraction (not limited to available water) - NOTE the unit is m3/day #
        self.potVolGroundwaterAbstract = pcr.min(remainingTotalDemand, groundwater_demand_estimate)                                    #
        #############################################################################################################################
        
        # constraining groundwater abstraction with the regional annual pumping capacity
        if groundwater.limitRegionalAnnualGroundwaterAbstraction:

            logger.debug('Total groundwater abstraction is limited by regional annual pumping capacity.')

            # estimate of total groundwater abstraction (m3) from the last 365 days:
            tolerating_days = 0.
            annualGroundwaterAbstraction = groundwater.avgAbstraction * routing.cellArea *\
                                           pcr.min(pcr.max(0.0, 365.0 - tolerating_days), routing.timestepsToAvgDischarge)
            # total groundwater abstraction (m3) from the last 365 days at the regional scale
            regionalAnnualGroundwaterAbstraction = pcr.areatotal(pcr.cover(annualGroundwaterAbstraction, 0.0), groundwater_pumping_region_ids)


            # the remaining pumping capacity (unit: m3) at the regional scale
            remainingRegionalAnnualGroundwaterAbstractionLimit = pcr.max(0.0, regionalAnnualGroundwaterAbstractionLimit - \
                                                                              regionalAnnualGroundwaterAbstraction)
            # considering safety factor (residence time in day-1)                                                                  
            remainingRegionalAnnualGroundwaterAbstractionLimit *= 0.33
            
            # the remaining pumping capacity (unit: m3) limited by self.potVolGroundwaterAbstract (at the regional scale)
            remainingRegionalAnnualGroundwaterAbstractionLimit = pcr.min(remainingRegionalAnnualGroundwaterAbstractionLimit,\
                                                                         pcr.areatotal(self.potVolGroundwaterAbstract, groundwater_pumping_region_ids))
            
            # the remaining pumping capacity (unit: m3) at the pixel scale - downscaled using self.potVolGroundwaterAbstract
            remainingPixelAnnualGroundwaterAbstractionLimit = remainingRegionalAnnualGroundwaterAbstractionLimit * \
                vos.getValDivZero(self.potVolGroundwaterAbstract, pcr.areatotal(self.potVolGroundwaterAbstract, groundwater_pumping_region_ids))
                
            # reduced (after pumping capacity) potential groundwater abstraction/demand (unit: m3) and considering the average recharge (baseflow) 
            self.potVolGroundwaterAbstract = pcr.min(self.potVolGroundwaterAbstract, \
                                      remainingPixelAnnualGroundwaterAbstractionLimit + pcr.max(0.0, routing.avgBaseflow ))

            
        else:
            logger.debug('NO LIMIT for regional groundwater (annual) pumping. It may result too high groundwater abstraction.')
        

        # Abstraction and Allocation of NON-FOSSIL GROUNDWATER
        # #############################################################################################################################
        # available storGroundwater (non fossil groundwater) that can be accessed (NOTE: All the following have the unit  m3)
        readAvlStorGroundwater = pcr.cover(pcr.max(0.00, groundwater.storGroundwater * sell.cellArea), 0.0) 
        # - considering maximum daily groundwater abstraction
        readAvlStorGroundwater = pcr.min(readAvlStorGroundwater, groundwater.maximumDailyGroundwaterAbstraction * sell.cellArea) 
        # - ignore groundwater storage in non-productive aquifer 
        readAvlStorGroundwater = pcr.ifthenelse(groundwater.productive_aquifer, readAvlStorGroundwater, 0.0)
        # for non-productive aquifer, reduce readAvlStorGroundwater to the current recharge/baseflow rate
        readAvlStorGroundwater = pcr.ifthenelse(groundwater.productive_aquifer, \
                                                readAvlStorGroundwater, pcr.min(readAvlStorGroundwater, pcr.max(routing.avgBaseflow * 24. * 3600., 0.0)))
        # avoid the condition that the entire groundwater volume abstracted instantaneously
        readAvlStorGroundwater *= 0.75



        # Abstraction and Allocation of RENEWABLE GROUNDWATER
        # ##################################################################################################################
        # - renewable groundwater to satisfy water demand
        if self.usingAllocationSegmentsForGroundwaterSource:
        #  
            logger.debug("Allocation of supply from renewable groundwater.")
        #  
            volRenewGroundwaterAbstraction, volRenewGroundwaterAllocation, volZoneRenewGroundwaterAbstraction = \
              waterAbstractionAndAllocation(
              water_demand_volume = self.potVolGroundwaterAbstract,\
              available_water_volume = readAvlStorGroundwater,\
              allocation_zones = self.allocationSegmentsForGroundwaterSource,\
              zone_area = self.allocationSegmentsForGroundwaterSourceAreas,\
              high_volume_treshold = None,\
              debug_water_balance = True,\
              extra_info_for_water_balance_reporting = str(currTimeStep.fulldate), 
              landmask = self.landmask,
              ignore_small_values = False,
              prioritizing_local_source = self.prioritizeLocalSourceToMeetWaterDemand)
        #     
        else: 
        #     
            logger.debug("Supply from renewable groundwater is only for satisfying local demand (no network).")
            volRenewGroundwaterAbstraction      = pcr.min(readAvlStorGroundwater, self.potVolGroundwaterAbstract)
            volRenewGroundwaterAllocation       = volRenewGroundwaterAbstraction
            volZoneRenewGroundwaterAbstraction  = volRenewGroundwaterAbstraction
        # ##################################################################################################################
        # - end of Abstraction and Allocation of RENEWABLE GROUNDWATER


        # allocate the "renewable groundwater Allocation" to each sector - unit: m3
        self.allocated_demand_per_sector["renewable_groundwater"] = self.allocate_satisfied_demand_to_each_sector(totalVolWaterAllocation = volRenewGroundwaterAllocation, sectoral_remaining_demand_volume = remaining_gross_sectoral_water_demands, total_remaining_demand_volume = remainingTotalDemand)


        # allocate the "renewable groundwater Abstraction" to each sector - unit: m3
        self.allocated_withdrawal_per_sector["renewable_groundwater"] = self.allocate_withdrawal_to_each_source(totalVolCellWaterAbstraction = volRenewGroundwaterAbstraction, totalVolZoneAbstraction = volZoneRenewGroundwaterAbstraction, cellAllocatedDemandPerSector = self.allocated_demand_per_sector["renewable_groundwater"], allocation_zones = self.allocationSegmentsForGroundwaterSource)
        
        
        # remaining renewable groundwater that can still be extracted - unit: m3
        self.volRemainingRenewGroundwater = pcr.max(0.0,  readAvlStorGroundwater - volRenewGroundwaterAbstraction)


        ################################################################################################################################
        # variable to reduce capillary rise in order to ensure there is always enough water to supply non fossil groundwater abstraction 
        # - unit: m
        self.reducedCapRise = volRenewGroundwaterAbstraction / sell.cellArea                            
        # TODO: Check do we need this for runs with MODFLOW ???
        ################################################################################################################################
        
        
        
        # TODO: Continue from this!!!


 


        ######################################################################################################################
        ######################################################################################################################
        # water demand that must be satisfied by fossil groundwater abstraction (unit: m, not limited to available water)
        self.potFossilGroundwaterAbstract = pcr.max(0.0, self.potGroundwaterAbstract - \
                                                         self.allocNonFossilGroundwater)
        ######################################################################################################################
        ######################################################################################################################


        # For a run using MODFLOW, the concept of fossil groundwater abstraction is abandoned (self.limitAbstraction == True):
        if groundwater.useMODFLOW or self.limitAbstraction:
            logger.debug('Fossil groundwater abstractions are NOT allowed')
            self.fossilGroundwaterAbstr = pcr.scalar(0.0)
            self.fossilGroundwaterAlloc = pcr.scalar(0.0)


        # Abstraction and Allocation of FOSSIL GROUNDWATER
        # #####################################################################################################################################

        if self.limitAbstraction == False:                              # TODO: For runs without any water use, we can exclude this. 
            
            logger.debug('Fossil groundwater abstractions are allowed.')
            
            # the remaining water demand (m/day) for all sectors - NOT limited to self.potFossilGroundwaterAbstract
            #####################################################################################################################
            # - for domestic 
            remainingDomestic   = pcr.max(0.0, nonIrrGrossDemandDict['potential_demand']['domestic']  - satisfiedDomesticDemand)
            # - for industry 
            remainingIndustry   = pcr.max(0.0, nonIrrGrossDemandDict['potential_demand']['industry']  - satisfiedIndustryDemand)
            # - for livestock 
            remainingLivestock  = pcr.max(0.0, nonIrrGrossDemandDict['potential_demand']['livestock'] - satisfiedLivestockDemand)
            # - for irrigation (excluding livestock)
            remainingIrrigation = pcr.max(0.0, self.irrGrossDemand - satisfiedIrrigationDemand) 
            # - total for livestock and irrigation
            remainingIrrigationLivestock = remainingIrrigation + remainingLivestock
            # - total for industrial and domestic (excluding livestock)
            remainingIndustrialDomestic  = remainingIndustry + remainingDomestic
            # - remaining total demand
            remainingTotalDemand = remainingIrrigationLivestock + remainingIndustrialDomestic                                                     


        # constraining fossil groundwater abstraction with regional pumping capacity
        if groundwater.limitRegionalAnnualGroundwaterAbstraction and self.limitAbstraction == False:

            logger.debug('Fossil groundwater abstraction is allowed, BUT limited by the regional annual pumping capacity.')

            # estimate of total groundwater abstraction (m3) from the last 365 days:
            # - considering abstraction from non fossil groundwater
            annualGroundwaterAbstraction += self.nonFossilGroundwaterAbs*routing.cellArea
            # at the regional scale
            regionalAnnualGroundwaterAbstraction = pcr.areatotal(pcr.cover(annualGroundwaterAbstraction, 0.0), groundwater_pumping_region_ids)
            
            # fossil groundwater demand/asbtraction reduced by pumping capacity (unit: m/day)
            # - safety factor to avoid the remaining limit abstracted at once (due to overestimation of groundwater demand)
            safety_factor_for_fossil_abstraction = 1.00
            self.potFossilGroundwaterAbstract *= pcr.min(1.00,\
                                                 pcr.cover(\
                                                 pcr.ifthenelse(regionalAnnualGroundwaterAbstractionLimit > 0.0,
                                                 pcr.max(0.000, regionalAnnualGroundwaterAbstractionLimit * safety_factor_for_fossil_abstraction-\
                                                                regionalAnnualGroundwaterAbstraction) /
                                                                regionalAnnualGroundwaterAbstractionLimit , 0.0), 0.0))

            #~ # Shall we will always try to fulfil the remaining industrial and domestic demand?
            #~ self.potFossilGroundwaterAbstract = pcr.max(remainingIndustrialDomestic, self.potFossilGroundwaterAbstract)



        if self.limitAbstraction == False:                              # TODO: For runs without any water use, we can exclude this. 


            ###############################################################################################################################
            # estimate the remaining total demand (unit: m/day) LIMITED to self.potFossilGroundwaterAbstract
            ###############################################################################################################################

            correctedRemainingTotalDemand = pcr.min(self.potFossilGroundwaterAbstract, remainingTotalDemand)

            # the remaining industrial and domestic demand and livestock (unit: m/day) limited to self.potFossilGroundwaterAbstract
            # - no correction, we will always try to fulfil these demands
            correctedRemainingIndustrialDomesticLivestock = pcr.min(remainingIndustrialDomestic + remainingLivestock, correctedRemainingTotalDemand)
            
            # the remaining irrigation demand limited to self.potFossilGroundwaterAbstract
            correctedRemainingIrrigation = pcr.min(remainingIrrigation, \
                                                    pcr.max(0.0, correctedRemainingTotalDemand - correctedRemainingIndustrialDomesticLivestock))
            # - ignore small irrigation demand (less than 1 mm)
            correctedRemainingIrrigation = pcr.rounddown(correctedRemainingIrrigation*1000.)/1000.
            
            # the (corrected) remaining total demand (limited to self.potFossilGroundwaterAbstract)
            correctedRemainingTotalDemand = correctedRemainingIndustrialDomesticLivestock + correctedRemainingIrrigation
            
            # the (corrected) remaining industrial and domestic demand (excluding livestock)
            correctedRemainingIndustrialDomestic = pcr.min(remainingIndustrialDomestic, correctedRemainingTotalDemand)

            # the remaining irrigation and livestock water demand limited to self.potFossilGroundwaterAbstract
            correctedRemainingIrrigationLivestock = pcr.min(remainingIrrigationLivestock, \
                                                    pcr.max(0.0, correctedRemainingTotalDemand - correctedRemainingIndustrialDomestic))
                                                  
            # the (corrected) remaining total demand (unit: m/day) limited to self.potFossilGroundwaterAbstract
            correctedRemainingTotalDemand = correctedRemainingIrrigationLivestock + correctedRemainingIndustrialDomestic
            
            # TODO: Do the water balance check: correctedRemainingIrrigationLivestock + correctedRemainingIndustrialDomestic <= self.potFossilGroundwaterAbstract                                          

            # constrain the irrigation groundwater demand with groundwater source fraction 
            correctedRemainingIrrigationLivestock = pcr.min((1.0 - swAbstractionFractionDict['irrigation']) * remainingIrrigationLivestock,\
                                                             correctedRemainingIrrigationLivestock) 
            correctedRemainingIrrigationLivestock = pcr.max(0.0,\
             pcr.min(correctedRemainingIrrigationLivestock,\
             pcr.max(0.0, totalIrrigationLivestockDemand) * (1.0 - swAbstractionFractionDict['irrigation']) - satisfiedIrrigationDemandFromNonFossilGroundwater))
            
            # ignore fossil groundwater abstraction in irrigation areas dominated by swAbstractionFractionDict['irrigation']
            correctedRemainingIrrigationLivestock = pcr.ifthenelse(\
                               swAbstractionFractionDict['irrigation'] >= swAbstractionFractionDict['treshold_to_minimize_fossil_groundwater_irrigation'], 0.0,\
                               correctedRemainingIrrigationLivestock)

            # reduce the fossil irrigation and livestock demands with enough supply of non fossil groundwater (in order to minimize unrealistic areas of fossil groundwater abstraction)
            # - supply from the average recharge (baseflow) and non fossil groundwater allocation 
            nonFossilGroundwaterSupply = pcr.max(pcr.max(0.0, routing.avgBaseflow) / routing.cellArea, \
                                                 groundwater.avgNonFossilAllocationShort, groundwater.avgNonFossilAllocation)  
            # - irrigation supply from the non fossil groundwater
            nonFossilIrrigationGroundwaterSupply  = nonFossilGroundwaterSupply * vos.getValDivZero(remainingIrrigationLivestock, remainingTotalDemand)
            # - the corrected/reduced irrigation and livestock demand
            correctedRemainingIrrigationLivestock = pcr.max(0.0, correctedRemainingIrrigationLivestock - nonFossilIrrigationGroundwaterSupply)

            # the corrected remaining total demand (unit: m/day) 
            correctedRemainingTotalDemand = correctedRemainingIndustrialDomestic + correctedRemainingIrrigationLivestock                                                                                                                                               

            ###############################################################################################################################

            # water demand that must be satisfied by fossil groundwater abstraction           
            self.potFossilGroundwaterAbstract = pcr.min(self.potFossilGroundwaterAbstract, correctedRemainingTotalDemand)
            
            if groundwater.limitFossilGroundwaterAbstraction == False and self.limitAbstraction == False:

                # Note: If limitFossilGroundwaterAbstraction == False, 
                #       allocation of fossil groundwater abstraction is not needed.  
                msg  = 'Fossil groundwater abstractions are without limit for satisfying local demand. '
                msg  = 'Allocation for fossil groundwater abstraction is NOT needed/implemented. '
                msg += 'However, the fossil groundwater abstraction rate still consider the maximumDailyGroundwaterAbstraction.'
                logger.debug(msg)
                
                # fossil groundwater abstraction (unit: m/day) 
                self.fossilGroundwaterAbstr = self.potFossilGroundwaterAbstract
                self.fossilGroundwaterAbstr = \
                 pcr.min(\
                 pcr.max(0.0, groundwater.maximumDailyGroundwaterAbstraction - self.nonFossilGroundwaterAbs), self.fossilGroundwaterAbstr)
                
                # fossil groundwater allocation (unit: m/day)
                self.fossilGroundwaterAlloc = self.fossilGroundwaterAbstr
        
            if groundwater.limitFossilGroundwaterAbstraction and self.limitAbstraction == False:

                logger.debug('Fossil groundwater abstractions are allowed, but with limit.')
                
                # accesible fossil groundwater (unit: m/day)
                readAvlFossilGroundwater = pcr.ifthenelse(groundwater.productive_aquifer, groundwater.storGroundwaterFossil, 0.0)
                # - residence time (day-1) or safety factor  (to avoid 'unrealistic' zero fossil groundwater)
                readAvlFossilGroundwater *= 0.10
                # - considering maximum daily groundwater abstraction
                readAvlFossilGroundwater = pcr.min(readAvlFossilGroundwater, groundwater.maximumDailyFossilGroundwaterAbstraction, \
                                           pcr.max(0.0, groundwater.maximumDailyGroundwaterAbstraction - self.nonFossilGroundwaterAbs))
                readAvlFossilGroundwater = pcr.max(pcr.cover(readAvlFossilGroundwater, 0.0), 0.0)                                           
                
                if groundwater.usingAllocSegments:
                
                    logger.debug('Allocation of fossil groundwater abstraction.')
                
                    # TODO: considering aquifer productivity while doing the allocation.

                    # fossil groundwater abstraction and allocation in volume (unit: m3)
                    volActGroundwaterAbstract, volAllocGroundwaterAbstract = \
                       vos.waterAbstractionAndAllocation(
                       water_demand_volume = self.potFossilGroundwaterAbstract*routing.cellArea,\
                       available_water_volume = pcr.max(0.00, readAvlFossilGroundwater*routing.cellArea),\
                       allocation_zones = groundwater.allocSegments,\
                       zone_area = groundwater.segmentArea,\
                       high_volume_treshold = None,\
                       debug_water_balance = True,\
                       extra_info_for_water_balance_reporting = str(currTimeStep.fulldate),  
                       landmask = self.landmask,
                       ignore_small_values = False,
                       prioritizing_local_source = self.prioritizeLocalSourceToMeetWaterDemand)
                    
                    # fossil groundwater abstraction and allocation in meter
                    self.fossilGroundwaterAbstr = volActGroundwaterAbstract  /routing.cellArea 
                    self.fossilGroundwaterAlloc = volAllocGroundwaterAbstract/routing.cellArea 
                
                else:
                    
                    logger.debug('Fossil groundwater abstraction is only for satisfying local demand. NO Allocation for fossil groundwater abstraction.')
                
                    self.fossilGroundwaterAbstr = pcr.min(pcr.max(0.0, readAvlFossilGroundwater), self.potFossilGroundwaterAbstract)
                    self.fossilGroundwaterAlloc = self.fossilGroundwaterAbstr 
        

            # water demand that have been satisfied (m/day) - after desalination, surface water, non fossil groundwater & fossil groundwater
            ################################################################################################################################
            
            # from fossil groundwater, we should prioritize domestic and industrial water demand
            prioritizeFossilGroundwaterForDomesticIndutrial = False                            # TODO: Define this in the configuration file.
            
            if prioritizeFossilGroundwaterForDomesticIndutrial:
                
                # - first priority: for industrial and domestic demand (excluding livestock)
                satisfiedIndustrialDomesticDemandFromFossilGroundwater = pcr.min(self.fossilGroundwaterAlloc, \
                                                                                 remainingIndustrialDomestic)
                # - for domestic                                                                 
                satisfiedDomesticDemand += satisfiedIndustrialDomesticDemandFromFossilGroundwater * vos.getValDivZero(remainingDomestic, \
                                                                                                                 remainingIndustrialDomestic)
                # - for industry
                satisfiedIndustryDemand += satisfiedIndustrialDomesticDemandFromFossilGroundwater * vos.getValDivZero(remainingIndustry, \
                                                                                                                 remainingIndustrialDomestic)             
                # - for irrigation and livestock demand
                satisfiedIrrigationLivestockDemandFromFossilGroundwater = pcr.max(0.0, self.fossilGroundwaterAlloc - \
                                                                                       satisfiedIndustrialDomesticDemandFromFossilGroundwater)
                # - for irrigation
                satisfiedIrrigationDemand += satisfiedIrrigationLivestockDemandFromFossilGroundwater * vos.getValDivZero(remainingIrrigation, \
                                                                                                                remainingIrrigationLivestock)
                # - for livestock
                satisfiedLivestockDemand  += satisfiedIrrigationLivestockDemandFromFossilGroundwater * vos.getValDivZero(remainingLivestock, \
                                                                                                                remainingIrrigationLivestock)
            
            else:
            
                # Distribute fossil water proportionaly based on the amount of each sector
                
                # - for irrigation and livestock water demand 
                satisfiedIrrigationLivestockDemandFromFossilGroundwater = self.fossilGroundwaterAlloc * \
                       vos.getValDivZero(correctedRemainingIrrigationLivestock, correctedRemainingTotalDemand)
                # - for irrigation water demand, but not including livestock 
                satisfiedIrrigationDemandFromFossilGroundwater = satisfiedIrrigationLivestockDemandFromFossilGroundwater * \
                       vos.getValDivZero(remainingIrrigation, remainingIrrigationLivestock)
                satisfiedIrrigationDemand += satisfiedIrrigationDemandFromFossilGroundwater
                # - for non irrigation water demand: livestock, domestic and industry 
                satisfiedNonIrrDemandFromFossilGroundwater = pcr.max(0.0, self.fossilGroundwaterAlloc - satisfiedIrrigationDemandFromFossilGroundwater)
                satisfiedNonIrrDemand += satisfiedNonIrrDemandFromFossilGroundwater
                # - for livestock                                                                      
                satisfiedLivestockDemand += pcr.max(0.0, satisfiedIrrigationLivestockDemandFromFossilGroundwater - \
                                                         satisfiedIrrigationDemandFromFossilGroundwater)
                # - for industrial and domestic demand (excluding livestock)
                satisfiedIndustrialDomesticDemandFromFossilGroundwater = pcr.max(0.0, self.fossilGroundwaterAlloc - \
                                                                                      satisfiedIrrigationLivestockDemandFromFossilGroundwater)
                # - for domestic                                                                 
                satisfiedDomesticDemand += satisfiedIndustrialDomesticDemandFromFossilGroundwater * vos.getValDivZero(remainingDomestic, \
                                                                                                                 remainingIndustrialDomestic)
                # - for industry
                satisfiedIndustryDemand += satisfiedIndustrialDomesticDemandFromFossilGroundwater * vos.getValDivZero(remainingIndustry, \
                                                                                                                 remainingIndustrialDomestic)             

        # water demand limited to available/allocated water
        self.totalPotentialGrossDemand = self.fossilGroundwaterAlloc +\
                                         self.allocNonFossilGroundwater +\
                                         self.allocSurfaceWaterAbstract +\
                                         self.desalinationAllocation

        # total groundwater abstraction and allocation (unit: m/day) 
        self.totalGroundwaterAllocation  = self.allocNonFossilGroundwater + self.fossilGroundwaterAlloc
        self.totalGroundwaterAbstraction = self.fossilGroundwaterAbstr + self.nonFossilGroundwaterAbs

        # irrigation water demand (excluding livestock) limited to available/allocated water (unit: m/day)
        self.irrGrossDemand = satisfiedIrrigationDemand                                  # not including livestock 
        
        # irrigation gross demand (m) per cover type (limited by available water)
        self.irrGrossDemandPaddy    = 0.0
        self.irrGrossDemandNonPaddy = 0.0
        if self.name == 'irrPaddy' or self.name == "irr_paddy": self.irrGrossDemandPaddy = self.irrGrossDemand
        if self.name == 'irrNonPaddy' or self.name == "irr_non_paddy" or self.name == "irr_non_paddy_crops": self.irrGrossDemandNonPaddy = self.irrGrossDemand

        # non irrigation water demand (including livestock) limited to available/allocated water (unit: m/day)
        self.nonIrrGrossDemand = pcr.max(0.0, \
                                 self.totalPotentialGrossDemand - self.irrGrossDemand)   # livestock, domestic and industry
        self.domesticWaterWithdrawal  = satisfiedDomesticDemand
        self.industryWaterWithdrawal  = satisfiedIndustryDemand
        self.livestockWaterWithdrawal = satisfiedLivestockDemand
        
        # return flow (unit: m/day) from non irrigation withdrawal (from domestic, industry and livestock)
        self.nonIrrReturnFlow = nonIrrGrossDemandDict['return_flow_fraction']['domestic'] * self.domesticWaterWithdrawal +\
                                nonIrrGrossDemandDict['return_flow_fraction']['industry'] * self.industryWaterWithdrawal +\
                                nonIrrGrossDemandDict['return_flow_fraction']['livestock']* self.livestockWaterWithdrawal
        # - ignore very small return flow (less than 0.1 mm)
        self.nonIrrReturnFlow = pcr.rounddown(self.nonIrrReturnFlow * 10000.)/10000.
        self.nonIrrReturnFlow = pcr.min(self.nonIrrReturnFlow, self.nonIrrGrossDemand)                        

        if self.debugWaterBalance:
            vos.waterBalanceCheck([self.irrGrossDemand,\
                                   self.nonIrrGrossDemand],\
                                  [self.totalPotentialGrossDemand],\
                                  [pcr.scalar(0.0)],\
                                  [pcr.scalar(0.0)] ,\
                                  'waterAllocationForAllSectors',True,\
                                   currTimeStep.fulldate,threshold=1e-4)
            vos.waterBalanceCheck([self.domesticWaterWithdrawal,\
                                   self.industryWaterWithdrawal,\
                                   self.livestockWaterWithdrawal],\
                                  [self.nonIrrGrossDemand],\
                                  [pcr.scalar(0.0)],\
                                  [pcr.scalar(0.0)] ,\
                                  'waterAllocationForNonIrrigationSectors',True,\
                                   currTimeStep.fulldate,threshold=1e-4)
            vos.waterBalanceCheck([self.irrGrossDemand,\
                                   self.domesticWaterWithdrawal,\
                                   self.industryWaterWithdrawal,\
                                   self.livestockWaterWithdrawal],\
                                  [self.totalPotentialGrossDemand],\
                                  [pcr.scalar(0.0)],\
                                  [pcr.scalar(0.0)] ,\
                                  'waterAllocationPerSector',True,\
                                   currTimeStep.fulldate,threshold=1e-4)
        
        # TODO: Perform water balance checks for all sources: desalination, surface water, non-fossil groundwater and fossil groundwater 



        
        

    # ~ def abstraction_and_allocation_from_renewable_groundwater():
        # ~ pass

    # ~ def abstraction_and_allocation_from_nonrenewable_groundwater():
        # ~ pass


    def get_allocation_zone(self, allocation_zone_input_file):

        # zones at which water allocation (surface and groundwater allocation) is determined
        self.usingAllocSegments = False
        self.allocSegments = None
        if iniItems.landSurfaceOptions['allocationSegmentsForGroundSurfaceWater']  != "None":
            self.usingAllocSegments = True 
            
            self.allocSegments = vos.readPCRmapClone(\
             iniItems.landSurfaceOptions['allocationSegmentsForGroundSurfaceWater'],
             self.cloneMap,self.tmpDir,self.inputDir,isLddMap=False,cover=None,isNomMap=True)
            self.allocSegments = pcr.ifthen(self.landmask, self.allocSegments)
            self.allocSegments = pcr.clump(self.allocSegments)
            
            extrapolate = True
            if "noParameterExtrapolation" in iniItems.landSurfaceOptions.keys() and iniItems.landSurfaceOptions["noParameterExtrapolation"] == "True": extrapolate = False

            if extrapolate:
                # extrapolate it 
                self.allocSegments = pcr.cover(self.allocSegments, \
                                               pcr.windowmajority(self.allocSegments, 0.5))

            self.allocSegments = pcr.ifthen(self.landmask, self.allocSegments)
            
            # clump it and cover the rests with cell ids 
            self.allocSegments = pcr.clump(self.allocSegments)
            cell_ids = pcr.mapmaximum(pcr.scalar(self.allocSegments)) + pcr.scalar(100.0) + pcr.uniqueid(pcr.boolean(1.0))
            self.allocSegments = pcr.cover(self.allocSegments, pcr.nominal(cell_ids))                               
            self.allocSegments = pcr.clump(self.allocSegments)
            self.allocSegments = pcr.ifthen(self.landmask, self.allocSegments)

            # cell area (unit: m2)
            cellArea = vos.readPCRmapClone(\
              iniItems.routingOptions['cellAreaMap'],
              self.cloneMap,self.tmpDir,self.inputDir)
            cellArea = pcr.ifthen(self.landmask, cellArea)

            # zonal/segment area (unit: m2)
            self.segmentArea = pcr.areatotal(pcr.cover(cellArea, 0.0), self.allocSegments)
            self.segmentArea = pcr.ifthen(self.landmask, self.segmentArea)

        else:

            logger.info("If there is any, water demand is satisfied by local source only.")


    def partitioningGroundSurfaceAbstraction(self, average_discharge_in_m3ps, average_local_baseflow_in_m3ps):

        # partitioning abstraction sources: groundwater and surface water
        # de Graaf et al., 2014 principle: partitioning based on local average baseflow (m3/s) and upstream average discharge (m3/s) 
        # - estimates of fractions of groundwater and surface water abstractions 
        averageBaseflowInput = average_local_baseflow_in_m3ps
        averageUpstreamInput = pcr.max(average_discharge_in_m3ps, pcr.cover(pcr.upstream(self.lddMap, average_discharge_in_m3ps), 0.0))
        
        if self.usingAllocSegments:
            
            averageBaseflowInput = pcr.max(0.0, pcr.ifthen(self.landmask, averageBaseflowInput))
            averageUpstreamInput = pcr.max(0.0, pcr.ifthen(self.landmask, averageUpstreamInput))
            
            averageBaseflowInput = pcr.cover(pcr.areaaverage(averageBaseflowInput, self.allocSegments), 0.0)
            averageUpstreamInput = pcr.cover(pcr.areamaximum(averageUpstreamInput, self.allocSegments), 0.0)

        else:
            logger.debug("Water demand can only be satisfied by local source.")

        swAbstractionFraction = vos.getValDivZero(\
                                averageUpstreamInput, 
                                averageUpstreamInput+averageBaseflowInput, vos.smallNumber)
        swAbstractionFraction = pcr.roundup(swAbstractionFraction*100.)/100.
        swAbstractionFraction = pcr.max(0.0, swAbstractionFraction)
        swAbstractionFraction = pcr.min(1.0, swAbstractionFraction)

        if self.usingAllocSegments:
            swAbstractionFraction = pcr.areamaximum(swAbstractionFraction, self.allocSegments)
            
        swAbstractionFraction = pcr.cover(swAbstractionFraction, 1.0)
        swAbstractionFraction = pcr.ifthen(self.landmask, swAbstractionFraction)
        
        # making a dictionary containing the surface water fraction for various purpose 
        swAbstractionFractionDict = {}
        # - the default estimate (based on de Graaf et al., 2014)
        swAbstractionFractionDict['estimate'] = swAbstractionFraction
        # - for irrigation and livestock purpose
        swAbstractionFractionDict['irrigation'] = swAbstractionFraction
        # - for industrial and domestic purpose
        swAbstractionFractionDict['max_for_non_irrigation'] = swAbstractionFraction
        #
        # - a treshold fraction value to optimize/maximize surface water withdrawal for irrigation 
        #   Principle: Areas with swAbstractionFractionDict['irrigation'] above this treshold will prioritize surface water use for irrigation purpose.
        #              A zero treshold value will ignore this principle.    
        swAbstractionFractionDict['treshold_to_maximize_irrigation_surface_water'] = self.treshold_to_maximize_irrigation_surface_water
        #
        # - a treshold fraction value to minimize fossil groundwater withdrawal, particularly to remove the unrealistic areas of fossil groundwater abstraction
        #   Principle: Areas with swAbstractionFractionDict['irrigation'] above this treshold will not extract fossil groundwater.
        swAbstractionFractionDict['treshold_to_minimize_fossil_groundwater_irrigation'] = self.treshold_to_minimize_fossil_groundwater_irrigation
        

        # the default value of surface water source fraction is None or not defined (in this case, this value will be the 'estimate' and limited with 'max_for_non_irrigation')
        swAbstractionFractionDict['non_irrigation'] = None       

        # incorporating the pre-defined fraction of surface water sources (e.g. based on Siebert et al., 2014 and McDonald et al., 2014)  
        if self.swAbstractionFractionData is not None:
            
            logger.debug('Using/incorporating the predefined fractions of surface water source.')
            swAbstractionFractionDict['estimate']   = swAbstractionFraction
            swAbstractionFractionDict['irrigation'] = self.partitioningGroundSurfaceAbstractionForIrrigation(swAbstractionFraction,\
                                                                                                             self.swAbstractionFractionData,\
                                                                                                             self.swAbstractionFractionDataQuality)
            swAbstractionFractionDict['max_for_non_irrigation'] = self.maximumNonIrrigationSurfaceWaterAbstractionFractionData
            
            if self.predefinedNonIrrigationSurfaceWaterAbstractionFractionData is not None:
                swAbstractionFractionDict['non_irrigation'] = pcr.cover(
                                                              self.predefinedNonIrrigationSurfaceWaterAbstractionFractionData, \
                                                              swAbstractionFractionDict['estimate'])
                swAbstractionFractionDict['non_irrigation'] = pcr.min(\
                                  swAbstractionFractionDict['non_irrigation'], \
                                  swAbstractionFractionDict['max_for_non_irrigation'])                                              

        else:    

            logger.debug('NOT using/incorporating the predefined fractions of surface water source.')

        return swAbstractionFractionDict

    def partitioningGroundSurfaceAbstractionForIrrigation(self,\
                                                          swAbstractionFractionEstimate,\
                                                          swAbstractionFractionData,\
                                                          swAbstractionFractionDataQuality):

        # surface water source fraction based on Stefan Siebert's map: 
        factor = 0.5 # using this factor, the minimum value for the following 'data_weight_value' is 0.75 (for swAbstractionFractionDataQuality == 5) 
        data_weight_value = pcr.scalar(1.0) - \
                           (pcr.min(5., pcr.max(0.0, swAbstractionFractionDataQuality))/10.0)*factor
                            
        swAbstractionFractionForIrrigation = data_weight_value  * swAbstractionFractionData +\
                                      (1.0 - data_weight_value) * swAbstractionFractionEstimate
        
        swAbstractionFractionForIrrigation = pcr.cover(swAbstractionFractionForIrrigation, swAbstractionFractionEstimate)
        swAbstractionFractionForIrrigation = pcr.cover(swAbstractionFractionForIrrigation, 1.0)
        swAbstractionFractionForIrrigation = pcr.ifthen(self.landmask, swAbstractionFractionForIrrigation)
        
        return swAbstractionFractionForIrrigation                  



    def update_ALL():

		# this is taken from some parts in the landCover.py

        # total irrigation gross demand (m) per cover types (not limited by available water)
        self.totalPotentialMaximumIrrGrossDemandPaddy    = 0.0
        self.totalPotentialMaximumIrrGrossDemandNonPaddy = 0.0
        if self.name == 'irrPaddy' or self.name == 'irr_paddy': self.totalPotentialMaximumIrrGrossDemandPaddy = self.irrGrossDemand
        if self.name == 'irrNonPaddy' or self.name == 'irr_non_paddy' or self.name == 'irr_non_paddy_crops': self.totalPotentialMaximumIrrGrossDemandNonPaddy = self.irrGrossDemand

        # non irrigation demand is only calculated for areas with fracVegCover > 0                   # DO WE NEED THIS ?
        nonIrrGrossDemandDict['potential_demand']['domestic']  = pcr.ifthenelse(self.fracVegCover > 0.0, nonIrrGrossDemandDict['potential_demand']['domestic'] , 0.0) 
        nonIrrGrossDemandDict['potential_demand']['industry']  = pcr.ifthenelse(self.fracVegCover > 0.0, nonIrrGrossDemandDict['potential_demand']['industry'] , 0.0)
        nonIrrGrossDemandDict['potential_demand']['livestock'] = pcr.ifthenelse(self.fracVegCover > 0.0, nonIrrGrossDemandDict['potential_demand']['livestock'], 0.0)
        
        # non irrigation water demand, including the livestock (not limited by available water)
        self.nonIrrGrossDemand = nonIrrGrossDemandDict['potential_demand']['domestic'] +\
                                 nonIrrGrossDemandDict['potential_demand']['industry'] +\
                                 nonIrrGrossDemandDict['potential_demand']['livestock']
                                 
        # total irrigation and livestock demand (not limited by available water)
        totalIrrigationLivestockDemand = self.irrGrossDemand + nonIrrGrossDemandDict['potential_demand']['livestock']
        
        # totalGrossDemand (m): irrigation and non irrigation (not limited by available water) - these values will not be reduced
        self.totalPotentialMaximumGrossDemand       = self.irrGrossDemand + self.nonIrrGrossDemand
        # - irrigation (excluding livestock)
        self.totalPotentialMaximumIrrGrossDemand    = self.irrGrossDemand                         
        # - non irrigation (including livestock)
        self.totalPotentialMaximumNonIrrGrossDemand = self.nonIrrGrossDemand
        
        # the following value will be reduced by available/accesible water
        self.totalPotentialGrossDemand           = self.totalPotentialMaximumGrossDemand         

        # Abstraction and Allocation of DESALINATED WATER
        # ##################################################################################################################
        # - desalination water to satisfy water demand
        if self.usingAllocSegments: # using zone/segments at which networks are defined (as defined in the landSurface options)
        #  
            logger.debug("Allocation of supply from desalination water.")
        #  
            volDesalinationAbstraction, volDesalinationAllocation = \
              vos.waterAbstractionAndAllocation(
              water_demand_volume = self.totalPotentialGrossDemand*routing.cellArea,\
              available_water_volume = pcr.max(0.00, desalinationWaterUse*routing.cellArea),\
              allocation_zones = allocSegments,\
              zone_area = self.segmentArea,\
              high_volume_treshold = None,\
              debug_water_balance = True,\
              extra_info_for_water_balance_reporting = str(currTimeStep.fulldate), 
              landmask = self.landmask,
              ignore_small_values = False,
              prioritizing_local_source = self.prioritizeLocalSourceToMeetWaterDemand)
        #     
            self.desalinationAbstraction = volDesalinationAbstraction / routing.cellArea
            self.desalinationAllocation  = volDesalinationAllocation  / routing.cellArea
        #     
        else: 
        #     
            logger.debug("Supply from desalination water is only for satisfying local demand (no network).")
            self.desalinationAbstraction = pcr.min(desalinationWaterUse, self.totalPotentialGrossDemand)
            self.desalinationAllocation  = self.desalinationAbstraction
        #     
        self.desalinationAbstraction = pcr.ifthen(self.landmask, self.desalinationAbstraction)
        self.desalinationAllocation  = pcr.ifthen(self.landmask, self.desalinationAllocation)
        # ##################################################################################################################
        # - end of Abstraction and Allocation of DESALINATED WATER


        # water demand that have been satisfied (unit: m/day) - after desalination
        ################################################################################################################################
        # - for irrigation (excluding livestock)
        satisfiedIrrigationDemand = vos.getValDivZero(self.irrGrossDemand, self.totalPotentialGrossDemand) * self.desalinationAllocation
        # - for domestic, industry and livestock
        satisfiedNonIrrDemand     = pcr.max(0.00, self.desalinationAllocation - satisfiedIrrigationDemand)
        # - for domestic
        satisfiedDomesticDemand   = satisfiedNonIrrDemand * vos.getValDivZero(nonIrrGrossDemandDict['potential_demand']['domestic'], 
                                                                              self.totalPotentialMaximumNonIrrGrossDemand)  
        # - for industry
        satisfiedIndustryDemand   = satisfiedNonIrrDemand * vos.getValDivZero(nonIrrGrossDemandDict['potential_demand']['industry'], 
                                                                              self.totalPotentialMaximumNonIrrGrossDemand)
        # - for livestock                                                                      
        satisfiedLivestockDemand  = pcr.max(0.0, satisfiedNonIrrDemand - satisfiedDomesticDemand - satisfiedIndustryDemand)


        # total remaining gross demand (m/day) after desalination
        ################################################################################################################################
        self.totalGrossDemandAfterDesalination = pcr.max(0.0, self.totalPotentialGrossDemand - self.desalinationAllocation)
        # the remaining water demand per sector
        # - for domestic 
        remainingDomestic   = pcr.max(0.0, nonIrrGrossDemandDict['potential_demand']['domestic']  - satisfiedDomesticDemand)
        # - for industry 
        remainingIndustry   = pcr.max(0.0, nonIrrGrossDemandDict['potential_demand']['industry']  - satisfiedIndustryDemand)
        # - for livestock 
        remainingLivestock  = pcr.max(0.0, nonIrrGrossDemandDict['potential_demand']['livestock'] - satisfiedLivestockDemand)
        # - for irrigation (excluding livestock)
        remainingIrrigation = pcr.max(0.0, self.irrGrossDemand - satisfiedIrrigationDemand) 
        # - total for livestock and irrigation
        remainingIrrigationLivestock = remainingIrrigation + remainingLivestock
        # - total for industrial and domestic (excluding livestock)
        remainingIndustrialDomestic  = pcr.max(0.0, self.totalGrossDemandAfterDesalination - remainingIrrigationLivestock)                                                     


        # Abstraction and Allocation of SURFACE WATER
        ##############################################################################################################################
        # calculate the estimate of surface water demand (considering by swAbstractionFractionDict)
        # - for industrial and domestic
        swAbstractionFraction_industrial_domestic = pcr.min(swAbstractionFractionDict['max_for_non_irrigation'],\
                                                            swAbstractionFractionDict['estimate'])
        if swAbstractionFractionDict['non_irrigation'] is not None:
            swAbstractionFraction_industrial_domestic = swAbstractionFractionDict['non_irrigation']

        surface_water_demand_estimate = swAbstractionFraction_industrial_domestic * remainingIndustrialDomestic
        # - for irrigation and livestock 
        surface_water_irrigation_demand_estimate = swAbstractionFractionDict['irrigation'] * remainingIrrigationLivestock
        # - surface water source as priority if groundwater irrigation fraction is relatively low  
        surface_water_irrigation_demand_estimate = \
           pcr.ifthenelse(swAbstractionFractionDict['irrigation'] >= swAbstractionFractionDict['treshold_to_maximize_irrigation_surface_water'],\
           remainingIrrigationLivestock, surface_water_irrigation_demand_estimate)
        # - update estimate of surface water demand withdrawal (unit: m/day)
        surface_water_demand_estimate += surface_water_irrigation_demand_estimate
        # - prioritize surface water use in non productive aquifers that have limited groundwater supply
        surface_water_demand_estimate = pcr.ifthenelse(groundwater.productive_aquifer, surface_water_demand_estimate,\
                                                       pcr.max(0.0, remainingIrrigationLivestock - \
                                                       pcr.min(groundwater.avgAllocationShort, groundwater.avgAllocation)))
        # - maximize/optimize surface water use in areas with the overestimation of groundwater supply 
        surface_water_demand_estimate += pcr.max(0.0, pcr.max(groundwater.avgAllocationShort, groundwater.avgAllocation) -\
               (1.0 - swAbstractionFractionDict['irrigation']) * totalIrrigationLivestockDemand -\
               (1.0 - swAbstractionFraction_industrial_domestic) * (self.totalPotentialMaximumGrossDemand - totalIrrigationLivestockDemand))
        #
        # total demand (unit: m/day) that should be allocated from surface water 
        # (corrected/limited by swAbstractionFractionDict and limited by the remaining demand)
        surface_water_demand_estimate         = pcr.min(self.totalGrossDemandAfterDesalination, surface_water_demand_estimate)
        correctedRemainingIrrigationLivestock = pcr.min(surface_water_demand_estimate, remainingIrrigationLivestock)
        correctedRemainingIndustrialDomestic  = pcr.min(remainingIndustrialDomestic,\
                                                pcr.max(0.0, surface_water_demand_estimate - remainingIrrigationLivestock))
        correctedSurfaceWaterDemandEstimate   = correctedRemainingIrrigationLivestock + correctedRemainingIndustrialDomestic
        surface_water_demand = correctedSurfaceWaterDemandEstimate
        #
        # if surface water abstraction as the first priority
        if self.surfaceWaterPiority: surface_water_demand = self.totalGrossDemandAfterDesalination
        #
        if self.usingAllocSegments:      # using zone/segment at which supply network is defined
        #  
            logger.debug("Allocation of surface water abstraction.")
        #  
            volActSurfaceWaterAbstract, volAllocSurfaceWaterAbstract = \
             vos.waterAbstractionAndAllocation(
             water_demand_volume = surface_water_demand*routing.cellArea,\
             available_water_volume = pcr.max(0.00, routing.readAvlChannelStorage),\
             allocation_zones = allocSegments,\
             zone_area = self.segmentArea,\
             high_volume_treshold = None,\
             debug_water_balance = True,\
             extra_info_for_water_balance_reporting = str(currTimeStep.fulldate), 
             landmask = self.landmask,
             ignore_small_values = False,
             prioritizing_local_source = self.prioritizeLocalSourceToMeetWaterDemand)

            self.actSurfaceWaterAbstract   = volActSurfaceWaterAbstract / routing.cellArea
            self.allocSurfaceWaterAbstract = volAllocSurfaceWaterAbstract / routing.cellArea
        #  
        else: 
            logger.debug("Surface water abstraction is only to satisfy local demand (no surface water network).")
            self.actSurfaceWaterAbstract   = pcr.min(routing.readAvlChannelStorage/routing.cellArea,\
                                                     surface_water_demand)                            # unit: m
            self.allocSurfaceWaterAbstract = self.actSurfaceWaterAbstract                             # unit: m   
        #  
        self.actSurfaceWaterAbstract   = pcr.ifthen(self.landmask, self.actSurfaceWaterAbstract)
        self.allocSurfaceWaterAbstract = pcr.ifthen(self.landmask, self.allocSurfaceWaterAbstract)
        ################################################################################################################################
        # - end of Abstraction and Allocation of SURFACE WATER

        
        # water demand that have been satisfied (unit: m/day) - after desalination and surface water supply
        ################################################################################################################################
        # - for irrigation and livestock water demand 
        satisfiedIrrigationLivestockDemandFromSurfaceWater = self.allocSurfaceWaterAbstract * \
               vos.getValDivZero(correctedRemainingIrrigationLivestock, correctedSurfaceWaterDemandEstimate)
        # - for irrigation water demand, but not including livestock 
        satisfiedIrrigationDemandFromSurfaceWater = satisfiedIrrigationLivestockDemandFromSurfaceWater * \
               vos.getValDivZero(remainingIrrigation, remainingIrrigationLivestock)
        satisfiedIrrigationDemand += satisfiedIrrigationDemandFromSurfaceWater
        # - for non irrigation water demand: livestock, domestic and industry 
        satisfiedNonIrrDemandFromSurfaceWater = pcr.max(0.0, self.allocSurfaceWaterAbstract - satisfiedIrrigationDemandFromSurfaceWater)
        satisfiedNonIrrDemand += satisfiedNonIrrDemandFromSurfaceWater
        # - for livestock                                                                      
        satisfiedLivestockDemand += pcr.max(0.0, satisfiedIrrigationLivestockDemandFromSurfaceWater - \
                                                 satisfiedIrrigationDemandFromSurfaceWater)
        # - for industrial and domestic demand (excluding livestock)
        satisfiedIndustrialDomesticDemandFromSurfaceWater = pcr.max(0.0, self.allocSurfaceWaterAbstract -\
                                                                         satisfiedIrrigationLivestockDemandFromSurfaceWater)
        # - for domestic                                                                 
        satisfiedDomesticDemand += satisfiedIndustrialDomesticDemandFromSurfaceWater * vos.getValDivZero(remainingDomestic, \
                                                                                                         remainingIndustrialDomestic)
        # - for industry
        satisfiedIndustryDemand += satisfiedIndustrialDomesticDemandFromSurfaceWater * vos.getValDivZero(remainingIndustry, \
                                                                                                         remainingIndustrialDomestic)             



        ######################################################################################################################
        # water demand (unit: m) that must be satisfied by groundwater abstraction (not limited to available water)
        self.potGroundwaterAbstract = pcr.max(0.0, self.totalGrossDemandAfterDesalination - self.allocSurfaceWaterAbstract)
        ######################################################################################################################
        # water demand per sector 
        # - for domestic 
        remainingDomestic   = pcr.max(0.0, nonIrrGrossDemandDict['potential_demand']['domestic']  - satisfiedDomesticDemand)
        # - for industry 
        remainingIndustry   = pcr.max(0.0, nonIrrGrossDemandDict['potential_demand']['industry']  - satisfiedIndustryDemand)
        # - for livestock 
        remainingLivestock  = pcr.max(0.0, nonIrrGrossDemandDict['potential_demand']['livestock'] - satisfiedLivestockDemand)
        # - for irrigation (excluding livestock)
        remainingIrrigation = pcr.max(0.0, self.irrGrossDemand - satisfiedIrrigationDemand) 
        # - total for livestock and irrigation
        remainingIrrigationLivestock = remainingIrrigation + remainingLivestock
        # - total for industrial and domestic (excluding livestock)
        remainingIndustrialDomestic  = remainingIndustry + remainingDomestic                                                     
        


        # Abstraction and Allocation of GROUNDWATER (fossil and non fossil)
        #########################################################################################################################
        # estimating groundwater water demand:
        # - demand for industrial and domestic sectors 
        #   (all remaining demand for these sectors should be satisfied)
        groundwater_demand_estimate = remainingIndustrialDomestic
        # - demand for irrigation and livestock sectors
        #   (only part of them will be satisfied, as they may be too high due to the uncertainty in the irrigation scheme)
        irrigationLivestockGroundwaterDemand = pcr.min(remainingIrrigationLivestock, \
                                               pcr.max(0.0, \
                                               (1.0 - swAbstractionFractionDict['irrigation'])*totalIrrigationLivestockDemand))
        groundwater_demand_estimate += irrigationLivestockGroundwaterDemand


        #####################################################################################################
        # water demand that must be satisfied by groundwater abstraction (not limited to available water)
        self.potGroundwaterAbstract = pcr.min(self.potGroundwaterAbstract, groundwater_demand_estimate)
        #####################################################################################################
        
        # constraining groundwater abstraction with the regional annual pumping capacity
        if groundwater.limitRegionalAnnualGroundwaterAbstraction:

            logger.debug('Total groundwater abstraction is limited by regional annual pumping capacity.')

            # estimate of total groundwater abstraction (m3) from the last 365 days:
            tolerating_days = 0.
            annualGroundwaterAbstraction = groundwater.avgAbstraction * routing.cellArea *\
                                           pcr.min(pcr.max(0.0, 365.0 - tolerating_days), routing.timestepsToAvgDischarge)
            # total groundwater abstraction (m3) from the last 365 days at the regional scale
            regionalAnnualGroundwaterAbstraction = pcr.areatotal(pcr.cover(annualGroundwaterAbstraction, 0.0), groundwater_pumping_region_ids)

            #~ # reduction factor to reduce groundwater abstraction/demand
            #~ reductionFactorForPotGroundwaterAbstract = pcr.cover(\
                                                       #~ pcr.ifthenelse(regionalAnnualGroundwaterAbstractionLimit > 0.0,
                                                       #~ pcr.max(0.000, regionalAnnualGroundwaterAbstractionLimit -\
                                                                      #~ regionalAnnualGroundwaterAbstraction) /
                                                                      #~ regionalAnnualGroundwaterAbstractionLimit , 0.0), 0.0)

            #~ # reduced potential groundwater abstraction (after pumping capacity)
            #~ self.potGroundwaterAbstract = pcr.min(1.00, reductionFactorForPotGroundwaterAbstract) * self.potGroundwaterAbstract

            #~ # alternative: reduced potential groundwater abstraction (after pumping capacity) and considering the average recharge (baseflow)
            #~ potGroundwaterAbstract = pcr.min(1.00, reductionFactorForPotGroundwaterAbstract) * self.potGroundwaterAbstract
            #~ self.potGroundwaterAbstract = pcr.min(self.potGroundwaterAbstract, 
                                                       #~ potGroundwaterAbstract + pcr.max(0.0, routing.avgBaseflow / routing.cellArea))



            ################## NEW METHOD #################################################################################################################
            # the remaining pumping capacity (unit: m3) at the regional scale
            remainingRegionalAnnualGroundwaterAbstractionLimit = pcr.max(0.0, regionalAnnualGroundwaterAbstractionLimit - \
                                                                              regionalAnnualGroundwaterAbstraction)
            # considering safety factor (residence time in day-1)                                                                  
            remainingRegionalAnnualGroundwaterAbstractionLimit *= 0.33
            
            # the remaining pumping capacity (unit: m3) limited by self.potGroundwaterAbstract (at the regional scale)
            remainingRegionalAnnualGroundwaterAbstractionLimit = pcr.min(remainingRegionalAnnualGroundwaterAbstractionLimit,\
                                                                         pcr.areatotal(self.potGroundwaterAbstract * routing.cellArea, groundwater_pumping_region_ids))
            
            # the remaining pumping capacity (unit: m3) at the pixel scale - downscaled using self.potGroundwaterAbstract
            remainingPixelAnnualGroundwaterAbstractionLimit = remainingRegionalAnnualGroundwaterAbstractionLimit * \
                vos.getValDivZero(self.potGroundwaterAbstract * routing.cellArea, pcr.areatotal(self.potGroundwaterAbstract * routing.cellArea, groundwater_pumping_region_ids))
                
            # reduced (after pumping capacity) potential groundwater abstraction/demand (unit: m) and considering the average recharge (baseflow) 
            self.potGroundwaterAbstract = pcr.min(self.potGroundwaterAbstract, \
                                      remainingPixelAnnualGroundwaterAbstractionLimit/routing.cellArea + pcr.max(0.0, routing.avgBaseflow / routing.cellArea))
            ################## end of NEW METHOD (but still under development) ##########################################################################################################



            #~ # Shall we will always try to fulfil the industrial and domestic demand?
            #~ self.potGroundwaterAbstract = pcr.max(remainingIndustrialDomestic, self.potGroundwaterAbstract)

            
        else:
            logger.debug('NO LIMIT for regional groundwater (annual) pumping. It may result too high groundwater abstraction.')
        

        # Abstraction and Allocation of NON-FOSSIL GROUNDWATER
        # #############################################################################################################################
        # available storGroundwater (non fossil groundwater) that can be accessed (unit: m)
        readAvlStorGroundwater = pcr.cover(pcr.max(0.00, groundwater.storGroundwater), 0.0)
        # - considering maximum daily groundwater abstraction
        readAvlStorGroundwater = pcr.min(readAvlStorGroundwater, groundwater.maximumDailyGroundwaterAbstraction)
        # - ignore groundwater storage in non-productive aquifer 
        readAvlStorGroundwater = pcr.ifthenelse(groundwater.productive_aquifer, readAvlStorGroundwater, 0.0)
        
        # for non-productive aquifer, reduce readAvlStorGroundwater to the current recharge/baseflow rate
        readAvlStorGroundwater = pcr.ifthenelse(groundwater.productive_aquifer, \
                                                readAvlStorGroundwater, pcr.min(readAvlStorGroundwater, pcr.max(routing.avgBaseflow, 0.0)))
        
        # avoid the condition that the entire groundwater volume abstracted instantaneously
        readAvlStorGroundwater *= 0.75

        if groundwater.usingAllocSegments:

            logger.debug('Allocation of non fossil groundwater abstraction.')

            # TODO: considering aquifer productivity while doing the allocation (e.g. using aquifer transmissivity/conductivity)
            
            # non fossil groundwater abstraction and allocation in volume (unit: m3)
            volActGroundwaterAbstract, volAllocGroundwaterAbstract = \
             vos.waterAbstractionAndAllocation(
             water_demand_volume = self.potGroundwaterAbstract*routing.cellArea,\
             available_water_volume = pcr.max(0.00, readAvlStorGroundwater*routing.cellArea),\
             allocation_zones = groundwater.allocSegments,\
             zone_area = groundwater.segmentArea,\
             high_volume_treshold = None,\
             debug_water_balance = True,\
             extra_info_for_water_balance_reporting = str(currTimeStep.fulldate),  
             landmask = self.landmask,
             ignore_small_values = False,
             prioritizing_local_source = self.prioritizeLocalSourceToMeetWaterDemand)
            
            # non fossil groundwater abstraction and allocation in meter
            self.nonFossilGroundwaterAbs   = volActGroundwaterAbstract  / routing.cellArea 
            self.allocNonFossilGroundwater = volAllocGroundwaterAbstract/ routing.cellArea 

        else:
            
            logger.debug('Non fossil groundwater abstraction is only for satisfying local demand.')
            self.nonFossilGroundwaterAbs   = pcr.min(readAvlStorGroundwater, self.potGroundwaterAbstract) 
            self.allocNonFossilGroundwater = self.nonFossilGroundwaterAbs
        ################################################################################################################################
        # - end of Abstraction and Allocation of NON FOSSIL GROUNDWATER


        ################################################################################################################################
        # variable to reduce capillary rise in order to ensure there is always enough water to supply non fossil groundwater abstraction 
        self.reducedCapRise = self.nonFossilGroundwaterAbs                            
        # TODO: Check do we need this for runs with MODFLOW ???
        ################################################################################################################################


        
        # water demand that have been satisfied (unit: m/day) - after desalination, surface water and non-fossil groundwater supply 
        ################################################################################################################################
        # - for irrigation and livestock water demand 
        satisfiedIrrigationLivestockDemandFromNonFossilGroundwater = self.allocNonFossilGroundwater * \
               vos.getValDivZero(irrigationLivestockGroundwaterDemand, groundwater_demand_estimate)
        # - for irrigation water demand, but not including livestock 
        satisfiedIrrigationDemandFromNonFossilGroundwater = satisfiedIrrigationLivestockDemandFromNonFossilGroundwater * \
               vos.getValDivZero(remainingIrrigation, remainingIrrigationLivestock)
        satisfiedIrrigationDemand += satisfiedIrrigationDemandFromNonFossilGroundwater
         # - for non irrigation water demand: livestock, domestic and industry 
        satisfiedNonIrrDemandFromNonFossilGroundwater = pcr.max(0.0, self.allocNonFossilGroundwater - satisfiedIrrigationLivestockDemandFromNonFossilGroundwater)
        satisfiedNonIrrDemand += satisfiedNonIrrDemandFromNonFossilGroundwater
        # - for livestock                                                                      
        satisfiedLivestockDemand += pcr.max(0.0, satisfiedIrrigationLivestockDemandFromNonFossilGroundwater - \
                                                 satisfiedIrrigationDemandFromNonFossilGroundwater)
        # - for industrial and domestic demand (excluding livestock)
        satisfiedIndustrialDomesticDemandFromNonFossilGroundwater = pcr.max(0.0, self.allocNonFossilGroundwater -\
                                                                                 satisfiedIrrigationLivestockDemandFromNonFossilGroundwater)
        # - for domestic                                                                 
        satisfiedDomesticDemand += satisfiedIndustrialDomesticDemandFromNonFossilGroundwater * vos.getValDivZero(remainingDomestic, remainingIndustrialDomestic)
        # - for industry
        satisfiedIndustryDemand += satisfiedIndustrialDomesticDemandFromNonFossilGroundwater * vos.getValDivZero(remainingIndustry, remainingIndustrialDomestic)             



        ######################################################################################################################
        ######################################################################################################################
        # water demand that must be satisfied by fossil groundwater abstraction (unit: m, not limited to available water)
        self.potFossilGroundwaterAbstract = pcr.max(0.0, self.potGroundwaterAbstract - \
                                                         self.allocNonFossilGroundwater)
        ######################################################################################################################
        ######################################################################################################################


        # For a run using MODFLOW, the concept of fossil groundwater abstraction is abandoned (self.limitAbstraction == True):
        if groundwater.useMODFLOW or self.limitAbstraction:
            logger.debug('Fossil groundwater abstractions are NOT allowed')
            self.fossilGroundwaterAbstr = pcr.scalar(0.0)
            self.fossilGroundwaterAlloc = pcr.scalar(0.0)


        # Abstraction and Allocation of FOSSIL GROUNDWATER
        # #####################################################################################################################################

        if self.limitAbstraction == False:                              # TODO: For runs without any water use, we can exclude this. 
            
            logger.debug('Fossil groundwater abstractions are allowed.')
            
            # the remaining water demand (m/day) for all sectors - NOT limited to self.potFossilGroundwaterAbstract
            #####################################################################################################################
            # - for domestic 
            remainingDomestic   = pcr.max(0.0, nonIrrGrossDemandDict['potential_demand']['domestic']  - satisfiedDomesticDemand)
            # - for industry 
            remainingIndustry   = pcr.max(0.0, nonIrrGrossDemandDict['potential_demand']['industry']  - satisfiedIndustryDemand)
            # - for livestock 
            remainingLivestock  = pcr.max(0.0, nonIrrGrossDemandDict['potential_demand']['livestock'] - satisfiedLivestockDemand)
            # - for irrigation (excluding livestock)
            remainingIrrigation = pcr.max(0.0, self.irrGrossDemand - satisfiedIrrigationDemand) 
            # - total for livestock and irrigation
            remainingIrrigationLivestock = remainingIrrigation + remainingLivestock
            # - total for industrial and domestic (excluding livestock)
            remainingIndustrialDomestic  = remainingIndustry + remainingDomestic
            # - remaining total demand
            remainingTotalDemand = remainingIrrigationLivestock + remainingIndustrialDomestic                                                     


        # constraining fossil groundwater abstraction with regional pumping capacity
        if groundwater.limitRegionalAnnualGroundwaterAbstraction and self.limitAbstraction == False:

            logger.debug('Fossil groundwater abstraction is allowed, BUT limited by the regional annual pumping capacity.')

            # estimate of total groundwater abstraction (m3) from the last 365 days:
            # - considering abstraction from non fossil groundwater
            annualGroundwaterAbstraction += self.nonFossilGroundwaterAbs*routing.cellArea
            # at the regional scale
            regionalAnnualGroundwaterAbstraction = pcr.areatotal(pcr.cover(annualGroundwaterAbstraction, 0.0), groundwater_pumping_region_ids)
            
            # fossil groundwater demand/asbtraction reduced by pumping capacity (unit: m/day)
            # - safety factor to avoid the remaining limit abstracted at once (due to overestimation of groundwater demand)
            safety_factor_for_fossil_abstraction = 1.00
            self.potFossilGroundwaterAbstract *= pcr.min(1.00,\
                                                 pcr.cover(\
                                                 pcr.ifthenelse(regionalAnnualGroundwaterAbstractionLimit > 0.0,
                                                 pcr.max(0.000, regionalAnnualGroundwaterAbstractionLimit * safety_factor_for_fossil_abstraction-\
                                                                regionalAnnualGroundwaterAbstraction) /
                                                                regionalAnnualGroundwaterAbstractionLimit , 0.0), 0.0))

            #~ # Shall we will always try to fulfil the remaining industrial and domestic demand?
            #~ self.potFossilGroundwaterAbstract = pcr.max(remainingIndustrialDomestic, self.potFossilGroundwaterAbstract)



        if self.limitAbstraction == False:                              # TODO: For runs without any water use, we can exclude this. 


            ###############################################################################################################################
            # estimate the remaining total demand (unit: m/day) LIMITED to self.potFossilGroundwaterAbstract
            ###############################################################################################################################

            correctedRemainingTotalDemand = pcr.min(self.potFossilGroundwaterAbstract, remainingTotalDemand)

            # the remaining industrial and domestic demand and livestock (unit: m/day) limited to self.potFossilGroundwaterAbstract
            # - no correction, we will always try to fulfil these demands
            correctedRemainingIndustrialDomesticLivestock = pcr.min(remainingIndustrialDomestic + remainingLivestock, correctedRemainingTotalDemand)
            
            # the remaining irrigation demand limited to self.potFossilGroundwaterAbstract
            correctedRemainingIrrigation = pcr.min(remainingIrrigation, \
                                                    pcr.max(0.0, correctedRemainingTotalDemand - correctedRemainingIndustrialDomesticLivestock))
            # - ignore small irrigation demand (less than 1 mm)
            correctedRemainingIrrigation = pcr.rounddown(correctedRemainingIrrigation*1000.)/1000.
            
            # the (corrected) remaining total demand (limited to self.potFossilGroundwaterAbstract)
            correctedRemainingTotalDemand = correctedRemainingIndustrialDomesticLivestock + correctedRemainingIrrigation
            
            # the (corrected) remaining industrial and domestic demand (excluding livestock)
            correctedRemainingIndustrialDomestic = pcr.min(remainingIndustrialDomestic, correctedRemainingTotalDemand)

            # the remaining irrigation and livestock water demand limited to self.potFossilGroundwaterAbstract
            correctedRemainingIrrigationLivestock = pcr.min(remainingIrrigationLivestock, \
                                                    pcr.max(0.0, correctedRemainingTotalDemand - correctedRemainingIndustrialDomestic))
                                                  
            # the (corrected) remaining total demand (unit: m/day) limited to self.potFossilGroundwaterAbstract
            correctedRemainingTotalDemand = correctedRemainingIrrigationLivestock + correctedRemainingIndustrialDomestic
            
            # TODO: Do the water balance check: correctedRemainingIrrigationLivestock + correctedRemainingIndustrialDomestic <= self.potFossilGroundwaterAbstract                                          

            # constrain the irrigation groundwater demand with groundwater source fraction 
            correctedRemainingIrrigationLivestock = pcr.min((1.0 - swAbstractionFractionDict['irrigation']) * remainingIrrigationLivestock,\
                                                             correctedRemainingIrrigationLivestock) 
            correctedRemainingIrrigationLivestock = pcr.max(0.0,\
             pcr.min(correctedRemainingIrrigationLivestock,\
             pcr.max(0.0, totalIrrigationLivestockDemand) * (1.0 - swAbstractionFractionDict['irrigation']) - satisfiedIrrigationDemandFromNonFossilGroundwater))
            
            # ignore fossil groundwater abstraction in irrigation areas dominated by swAbstractionFractionDict['irrigation']
            correctedRemainingIrrigationLivestock = pcr.ifthenelse(\
                               swAbstractionFractionDict['irrigation'] >= swAbstractionFractionDict['treshold_to_minimize_fossil_groundwater_irrigation'], 0.0,\
                               correctedRemainingIrrigationLivestock)

            # reduce the fossil irrigation and livestock demands with enough supply of non fossil groundwater (in order to minimize unrealistic areas of fossil groundwater abstraction)
            # - supply from the average recharge (baseflow) and non fossil groundwater allocation 
            nonFossilGroundwaterSupply = pcr.max(pcr.max(0.0, routing.avgBaseflow) / routing.cellArea, \
                                                 groundwater.avgNonFossilAllocationShort, groundwater.avgNonFossilAllocation)  
            # - irrigation supply from the non fossil groundwater
            nonFossilIrrigationGroundwaterSupply  = nonFossilGroundwaterSupply * vos.getValDivZero(remainingIrrigationLivestock, remainingTotalDemand)
            # - the corrected/reduced irrigation and livestock demand
            correctedRemainingIrrigationLivestock = pcr.max(0.0, correctedRemainingIrrigationLivestock - nonFossilIrrigationGroundwaterSupply)

            # the corrected remaining total demand (unit: m/day) 
            correctedRemainingTotalDemand = correctedRemainingIndustrialDomestic + correctedRemainingIrrigationLivestock                                                                                                                                               

            ###############################################################################################################################

            # water demand that must be satisfied by fossil groundwater abstraction           
            self.potFossilGroundwaterAbstract = pcr.min(self.potFossilGroundwaterAbstract, correctedRemainingTotalDemand)
            
            if groundwater.limitFossilGroundwaterAbstraction == False and self.limitAbstraction == False:

                # Note: If limitFossilGroundwaterAbstraction == False, 
                #       allocation of fossil groundwater abstraction is not needed.  
                msg  = 'Fossil groundwater abstractions are without limit for satisfying local demand. '
                msg  = 'Allocation for fossil groundwater abstraction is NOT needed/implemented. '
                msg += 'However, the fossil groundwater abstraction rate still consider the maximumDailyGroundwaterAbstraction.'
                logger.debug(msg)
                
                # fossil groundwater abstraction (unit: m/day) 
                self.fossilGroundwaterAbstr = self.potFossilGroundwaterAbstract
                self.fossilGroundwaterAbstr = \
                 pcr.min(\
                 pcr.max(0.0, groundwater.maximumDailyGroundwaterAbstraction - self.nonFossilGroundwaterAbs), self.fossilGroundwaterAbstr)
                
                # fossil groundwater allocation (unit: m/day)
                self.fossilGroundwaterAlloc = self.fossilGroundwaterAbstr
        
            if groundwater.limitFossilGroundwaterAbstraction and self.limitAbstraction == False:

                logger.debug('Fossil groundwater abstractions are allowed, but with limit.')
                
                # accesible fossil groundwater (unit: m/day)
                readAvlFossilGroundwater = pcr.ifthenelse(groundwater.productive_aquifer, groundwater.storGroundwaterFossil, 0.0)
                # - residence time (day-1) or safety factor  (to avoid 'unrealistic' zero fossil groundwater)
                readAvlFossilGroundwater *= 0.10
                # - considering maximum daily groundwater abstraction
                readAvlFossilGroundwater = pcr.min(readAvlFossilGroundwater, groundwater.maximumDailyFossilGroundwaterAbstraction, \
                                           pcr.max(0.0, groundwater.maximumDailyGroundwaterAbstraction - self.nonFossilGroundwaterAbs))
                readAvlFossilGroundwater = pcr.max(pcr.cover(readAvlFossilGroundwater, 0.0), 0.0)                                           
                
                if groundwater.usingAllocSegments:
                
                    logger.debug('Allocation of fossil groundwater abstraction.')
                
                    # TODO: considering aquifer productivity while doing the allocation.

                    # fossil groundwater abstraction and allocation in volume (unit: m3)
                    volActGroundwaterAbstract, volAllocGroundwaterAbstract = \
                       vos.waterAbstractionAndAllocation(
                       water_demand_volume = self.potFossilGroundwaterAbstract*routing.cellArea,\
                       available_water_volume = pcr.max(0.00, readAvlFossilGroundwater*routing.cellArea),\
                       allocation_zones = groundwater.allocSegments,\
                       zone_area = groundwater.segmentArea,\
                       high_volume_treshold = None,\
                       debug_water_balance = True,\
                       extra_info_for_water_balance_reporting = str(currTimeStep.fulldate),  
                       landmask = self.landmask,
                       ignore_small_values = False,
                       prioritizing_local_source = self.prioritizeLocalSourceToMeetWaterDemand)
                    
                    # fossil groundwater abstraction and allocation in meter
                    self.fossilGroundwaterAbstr = volActGroundwaterAbstract  /routing.cellArea 
                    self.fossilGroundwaterAlloc = volAllocGroundwaterAbstract/routing.cellArea 
                
                else:
                    
                    logger.debug('Fossil groundwater abstraction is only for satisfying local demand. NO Allocation for fossil groundwater abstraction.')
                
                    self.fossilGroundwaterAbstr = pcr.min(pcr.max(0.0, readAvlFossilGroundwater), self.potFossilGroundwaterAbstract)
                    self.fossilGroundwaterAlloc = self.fossilGroundwaterAbstr 
        

            # water demand that have been satisfied (m/day) - after desalination, surface water, non fossil groundwater & fossil groundwater
            ################################################################################################################################
            
            # from fossil groundwater, we should prioritize domestic and industrial water demand
            prioritizeFossilGroundwaterForDomesticIndutrial = False                            # TODO: Define this in the configuration file.
            
            if prioritizeFossilGroundwaterForDomesticIndutrial:
                
                # - first priority: for industrial and domestic demand (excluding livestock)
                satisfiedIndustrialDomesticDemandFromFossilGroundwater = pcr.min(self.fossilGroundwaterAlloc, \
                                                                                 remainingIndustrialDomestic)
                # - for domestic                                                                 
                satisfiedDomesticDemand += satisfiedIndustrialDomesticDemandFromFossilGroundwater * vos.getValDivZero(remainingDomestic, \
                                                                                                                 remainingIndustrialDomestic)
                # - for industry
                satisfiedIndustryDemand += satisfiedIndustrialDomesticDemandFromFossilGroundwater * vos.getValDivZero(remainingIndustry, \
                                                                                                                 remainingIndustrialDomestic)             
                # - for irrigation and livestock demand
                satisfiedIrrigationLivestockDemandFromFossilGroundwater = pcr.max(0.0, self.fossilGroundwaterAlloc - \
                                                                                       satisfiedIndustrialDomesticDemandFromFossilGroundwater)
                # - for irrigation
                satisfiedIrrigationDemand += satisfiedIrrigationLivestockDemandFromFossilGroundwater * vos.getValDivZero(remainingIrrigation, \
                                                                                                                remainingIrrigationLivestock)
                # - for livestock
                satisfiedLivestockDemand  += satisfiedIrrigationLivestockDemandFromFossilGroundwater * vos.getValDivZero(remainingLivestock, \
                                                                                                                remainingIrrigationLivestock)
            
            else:
            
                # Distribute fossil water proportionaly based on the amount of each sector
                
                # - for irrigation and livestock water demand 
                satisfiedIrrigationLivestockDemandFromFossilGroundwater = self.fossilGroundwaterAlloc * \
                       vos.getValDivZero(correctedRemainingIrrigationLivestock, correctedRemainingTotalDemand)
                # - for irrigation water demand, but not including livestock 
                satisfiedIrrigationDemandFromFossilGroundwater = satisfiedIrrigationLivestockDemandFromFossilGroundwater * \
                       vos.getValDivZero(remainingIrrigation, remainingIrrigationLivestock)
                satisfiedIrrigationDemand += satisfiedIrrigationDemandFromFossilGroundwater
                # - for non irrigation water demand: livestock, domestic and industry 
                satisfiedNonIrrDemandFromFossilGroundwater = pcr.max(0.0, self.fossilGroundwaterAlloc - satisfiedIrrigationDemandFromFossilGroundwater)
                satisfiedNonIrrDemand += satisfiedNonIrrDemandFromFossilGroundwater
                # - for livestock                                                                      
                satisfiedLivestockDemand += pcr.max(0.0, satisfiedIrrigationLivestockDemandFromFossilGroundwater - \
                                                         satisfiedIrrigationDemandFromFossilGroundwater)
                # - for industrial and domestic demand (excluding livestock)
                satisfiedIndustrialDomesticDemandFromFossilGroundwater = pcr.max(0.0, self.fossilGroundwaterAlloc - \
                                                                                      satisfiedIrrigationLivestockDemandFromFossilGroundwater)
                # - for domestic                                                                 
                satisfiedDomesticDemand += satisfiedIndustrialDomesticDemandFromFossilGroundwater * vos.getValDivZero(remainingDomestic, \
                                                                                                                 remainingIndustrialDomestic)
                # - for industry
                satisfiedIndustryDemand += satisfiedIndustrialDomesticDemandFromFossilGroundwater * vos.getValDivZero(remainingIndustry, \
                                                                                                                 remainingIndustrialDomestic)             

        # water demand limited to available/allocated water
        self.totalPotentialGrossDemand = self.fossilGroundwaterAlloc +\
                                         self.allocNonFossilGroundwater +\
                                         self.allocSurfaceWaterAbstract +\
                                         self.desalinationAllocation

        # total groundwater abstraction and allocation (unit: m/day) 
        self.totalGroundwaterAllocation  = self.allocNonFossilGroundwater + self.fossilGroundwaterAlloc
        self.totalGroundwaterAbstraction = self.fossilGroundwaterAbstr + self.nonFossilGroundwaterAbs

        # irrigation water demand (excluding livestock) limited to available/allocated water (unit: m/day)
        self.irrGrossDemand = satisfiedIrrigationDemand                                  # not including livestock 
        
        # irrigation gross demand (m) per cover type (limited by available water)
        self.irrGrossDemandPaddy    = 0.0
        self.irrGrossDemandNonPaddy = 0.0
        if self.name == 'irrPaddy' or self.name == "irr_paddy": self.irrGrossDemandPaddy = self.irrGrossDemand
        if self.name == 'irrNonPaddy' or self.name == "irr_non_paddy" or self.name == "irr_non_paddy_crops": self.irrGrossDemandNonPaddy = self.irrGrossDemand

        # non irrigation water demand (including livestock) limited to available/allocated water (unit: m/day)
        self.nonIrrGrossDemand = pcr.max(0.0, \
                                 self.totalPotentialGrossDemand - self.irrGrossDemand)   # livestock, domestic and industry
        self.domesticWaterWithdrawal  = satisfiedDomesticDemand
        self.industryWaterWithdrawal  = satisfiedIndustryDemand
        self.livestockWaterWithdrawal = satisfiedLivestockDemand
        
        # return flow (unit: m/day) from non irrigation withdrawal (from domestic, industry and livestock)
        self.nonIrrReturnFlow = nonIrrGrossDemandDict['return_flow_fraction']['domestic'] * self.domesticWaterWithdrawal +\
                                nonIrrGrossDemandDict['return_flow_fraction']['industry'] * self.industryWaterWithdrawal +\
                                nonIrrGrossDemandDict['return_flow_fraction']['livestock']* self.livestockWaterWithdrawal
        # - ignore very small return flow (less than 0.1 mm)
        self.nonIrrReturnFlow = pcr.rounddown(self.nonIrrReturnFlow * 10000.)/10000.
        self.nonIrrReturnFlow = pcr.min(self.nonIrrReturnFlow, self.nonIrrGrossDemand)                        

        if self.debugWaterBalance:
            vos.waterBalanceCheck([self.irrGrossDemand,\
                                   self.nonIrrGrossDemand],\
                                  [self.totalPotentialGrossDemand],\
                                  [pcr.scalar(0.0)],\
                                  [pcr.scalar(0.0)] ,\
                                  'waterAllocationForAllSectors',True,\
                                   currTimeStep.fulldate,threshold=1e-4)
            vos.waterBalanceCheck([self.domesticWaterWithdrawal,\
                                   self.industryWaterWithdrawal,\
                                   self.livestockWaterWithdrawal],\
                                  [self.nonIrrGrossDemand],\
                                  [pcr.scalar(0.0)],\
                                  [pcr.scalar(0.0)] ,\
                                  'waterAllocationForNonIrrigationSectors',True,\
                                   currTimeStep.fulldate,threshold=1e-4)
            vos.waterBalanceCheck([self.irrGrossDemand,\
                                   self.domesticWaterWithdrawal,\
                                   self.industryWaterWithdrawal,\
                                   self.livestockWaterWithdrawal],\
                                  [self.totalPotentialGrossDemand],\
                                  [pcr.scalar(0.0)],\
                                  [pcr.scalar(0.0)] ,\
                                  'waterAllocationPerSector',True,\
                                   currTimeStep.fulldate,threshold=1e-4)
        
        # TODO: Perform water balance checks for all sources: desalination, surface water, non-fossil groundwater and fossil groundwater 
		
		pass
        
        
