import textgrid 

def export_to_textgrid(result, output_path):

    tg = textgrid.TextGrid()

    # Fin du dernier segment = durée totale
    max_time = result["segments"][-1]["end"]
    
    tier = textgrid.IntervalTier(name="Transcription", maxTime=max_time)
    
    for segment in result["segments"]:
        start = segment["start"]
        end = segment["end"]
        text = segment["text"]

        tier.addInterval(textgrid.Interval(start, end, text))

    tg.append(tier)
    tg.write(output_path)
