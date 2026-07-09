form Sauvegarde Segments
    text audio_file_path
    text textgrid_file_path
    integer tier
    integer start_from
    integer end_at
    text folder
    text prefix
    text suffix
endform

Read from file... 'audio_file_path$'
soundname$ = selected$ ("Sound", 1)

Read from file... 'textgrid_file_path$'
gridname$ = selected$ ("TextGrid", 1)

select TextGrid 'gridname$'
numberOfIntervals = Get number of intervals... tier
if start_from > numberOfIntervals
    exit There are not that many intervals in the IntervalTier!
endif
if end_at > numberOfIntervals or end_at = 0
    end_at = numberOfIntervals
endif

count = 1
for interval from start_from to end_at
    select TextGrid 'gridname$'
    intname$ = Get label of interval... tier interval
    
    check = 0
    if intname$ = "" or intname$ = " " or intname$ = newline$
        check = 1
    endif
    
    if check = 0
        intervalstart = Get starting point... tier interval
        intervalend = Get end point... tier interval
        
        select Sound 'soundname$'
        Extract part... intervalstart intervalend "rectangular" 1 "no"
        
        numero$ = right$ ("000" + fixed$(count, 0), 3)
        filename$ = soundname$ + "_" + numero$
        
        intervalfile$ = folder$ + "/" + prefix$ + filename$ + suffix$ + ".wav"
        
        Write to WAV file... 'intervalfile$'
        Remove
        count = count + 1
    endif
endfor

select Sound 'soundname$'
plus TextGrid 'gridname$'
Remove


#############################################################################################################
# This script saves each interval in the selected IntervalTier of a TextGrid to a separate WAV sound file.
# 
# The source sound must be a LongSound object, and both the TextGrid and 
# the LongSound must have identical names and they have to be selected in the Objects window
# before running the script.
# Files are named with the corresponding interval labels (plus a running index number when necessary).
#
# NOTE: Make sure that the interval labels do not contain forbidden characters!
# 
# This script is distributed under the GNU General Public License.
# Copyright 8.3.2002 Mietta Lennes
#
# Modified by Danielle Daidone 11/13/17 to output names of saved files and to automatically exclude 
# all empty intervals, intervals with a space, or intervals with a line break
#
# Modifié par Camille Benoit-Guyod (2026) pour l'inclure dans une pipeline Python