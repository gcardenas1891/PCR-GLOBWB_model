
set -x

cd /scratch/depfg/sutan101/data/GFSAD1KCM/edwin_process

rm -r *.tif
rm -r *.map
rm -r *


# convert from GFSAD1KCM.2010

gdalwarp -tr 0.00833333333333333333333333333333333333333333333333333333333333333333333333 0.00833333333333333333333333333333333333333333333333333333333333333333333333 -te -180 -90 180 90 -r near ../GFSAD1KCM.2010.001.2016348142550.tif GFSAD1KCM.2010.001.2016348142550_global_30sec.tif

pcrcalc irrigated_fraction.map = "if(scalar(GFSAD1KCM.2010.001.2016348142550_global_30sec.tif) eq 1, scalar(1.0), if( scalar(GFSAD1KCM.2010.001.2016348142550_global_30sec.tif) eq 2, scalar(1.0))   )"

pcrcalc irrigated_fraction.map = "min(1.0, max(0.0, cover(irrigated_fraction.map, 0.0)))"

mapattr -s -P yb2t irrigated_fraction.map


# split irrgated_fraction.map to paddy and non-paddy

#~ sutan101@gpu037.cluster:/scratch/depfg/sutan101/data/pcrglobwb2_input_release/version_2019_11_beta_extended/pcrglobwb2_input/global_05min/landSurface/landCover$ ls -lah irr*/*.map
#~ -rwxr-xr-x 1 sutan101 depfg 36M Nov 11  2019 irrNonPaddy/fractionNonPaddy.map
#~ -rwxr-xr-x 1 sutan101 depfg 36M Nov 11  2019 irrPaddy/fractionPaddy.map

gdalwarp -tr 0.00833333333333333333333333333333333333333333333333333333333333333333333333 0.00833333333333333333333333333333333333333333333333333333333333333333333333 -te -180 -90 180 90 /scratch/depfg/sutan101/data/pcrglobwb2_input_release/version_2019_11_beta_extended/pcrglobwb2_input/global_05min/landSurface/landCover/irrNonPaddy/fractionNonPaddy.map fractionNonPaddy_05min_30sec.tif

gdalwarp -tr 0.00833333333333333333333333333333333333333333333333333333333333333333333333 0.00833333333333333333333333333333333333333333333333333333333333333333333333 -te -180 -90 180 90 /scratch/depfg/sutan101/data/pcrglobwb2_input_release/version_2019_11_beta_extended/pcrglobwb2_input/global_05min/landSurface/landCover/irrPaddy/fractionPaddy.map fractionPaddy_05min_30sec.tif

pcrcalc fractionNonPaddy_05min_30sec.map = "cover(min(1.0, fractionNonPaddy_05min_30sec.tif),0.0)"

pcrcalc fractionPaddy_05min_30sec.map    = "cover(min(1.0, fractionPaddy_05min_30sec.tif),0.0)"

mapattr -s -P yb2t *.map

pcrcalc fractionPaddy_30sec.map = "max(0.0, min(1.0, irrigated_fraction.map * if( (fractionNonPaddy_05min_30sec.map + fractionPaddy_05min_30sec.map) > 0.0, fractionPaddy_05min_30sec.map / (fractionNonPaddy_05min_30sec.map + fractionPaddy_05min_30sec.map), 0.0 )))"
pcrcalc fractionNonPaddy_30sec.map = "max(0.0, min(1.0, irrigated_fraction.map - fractionPaddy_30sec.map ))"

mapattr -s -P yb2t *.map

aguila fractionPaddy_30sec.map fractionNonPaddy_30sec.map irrigated_fraction.map

set +x