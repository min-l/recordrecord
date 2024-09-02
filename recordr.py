# 

import sys
from pydub import AudioSegment, silence
import discogs_client
import music_tag
import urllib.request
import PIL
import os
import json
from ffmpeg import FFmpeg
from tkinter import *
from tkinter import filedialog
from tkinter import ttk
import webbrowser

with open("config.json","r") as config_file:
    config = json.loads(config_file.read())

TBS = config["time_before_song"]
ST = config["silence_threshold"]
FF = config["file_format"]
FE = config["file_extension"]





def clver():
    # SECTION A
    with open("discogstoken2",'r') as token_file:
        token = token_file.read().strip()

    d = discogs_client.Client('mintyrecordmetadata/0.1', user_token=token)


    query = input("Search for name of Album or Release >")

    results = d.search(query,type='release',format='Vinyl')
    i = 0
    found = False
    collection_text = ''
    for result in results:
        #print(result)
        if found == False:
            if len(d.identity().collection_items(result.id)) > 0:
                found = True
                collection_text = ' <<IN COLLECTION>>'
            else:
                collection_text = ' <<NOT FOUND>>'
        print(str(i) + ' ==> ' + result.labels[0].catno + ': ' + result.artists[0].name + ' - ' + result.title + ' (' + result.country + ') - ' + result.formats[0]['name'] + ' - Discogs url: https://www.discogs.com/release/' + str(result.id) + collection_text)
        #print(result.country)
        #print(result.formats[0]['name'])
        i += 1
        collection_text = ' <<UNCHECKED>>'

    option = -1
    while option < 0 or option >= len(results):
        try:
            option = int(input('Select number >'))
        except:
            print('Select valid number')

    album_id = results[option].id


        


    # SECTION B
    album = d.release(album_id)
    tracklist = album.tracklist

    if tracklist[0].position != 'A1':
        print('something is wrong?')

    side = ''
    while side != 'A' and side != 'B':
        side = input('Select side (A or B) >').upper()


    side_tracklist = []

    first_track_no = -1
    c_track_no = 1
    for track in tracklist:
        if track.position[0] == side:
            side_tracklist.append(track)
            if first_track_no == -1:
                first_track_no = c_track_no
        c_track_no += 1

    for track in side_tracklist:
        print(track)

    mus_position = 0.0
    song_starts = []

    argv = sys.argv
    filename = str(argv[1])

    recordfile = AudioSegment.from_file(filename)

    print('Finding breaks in file (may take some time)')
    silence = silence.detect_silence(recordfile, min_silence_len=1000, silence_thresh=ST, seek_step=10)

    silence = [((start/1000),(stop/1000)) for start,stop in silence] #convert to sec



    # print(silence)



    for i in range(0,len(side_tracklist)-1):
        print('Song ' + side_tracklist[i].position + ' (' + side_tracklist[i].title + ') starts at ' + str(mus_position))
        next_silence = [(stop,stop-start) for start,stop in silence if stop > mus_position]
        print('Select start position for song ' + side_tracklist[i+1].position + ' (' + side_tracklist[i+1].title + ')')
        for j,s in enumerate(next_silence):
            print(str(j) + ': ' + str(s[0]) + 's (' + str(int(s[0])//60) + 'm ' + str(int(s[0]) % 60) +'s) - Gap duration: ' + str(round(s[1],2)) + 's')
        option = -1
        while option < 0 or option >= len(next_silence):
            try:
                option = int(input('>'))
            except:
                print('Select valid number')
        mus_position = next_silence[option][0]
        song_starts.append(mus_position)

    song_starts = [song - TBS for song in song_starts]

    song_starts.insert(0,0.0)

    print(song_starts)
    for i in range(0,len(song_starts) - 1):
        song_audio = recordfile[song_starts[i]*1000:song_starts[i+1]*1000]
        song_audio.export(str(i) + FE,format=FF)


    song_audio = recordfile[song_starts[len(song_starts) - 1]*1000:]
    song_audio.export(str(len(song_starts) - 1) + FE,format=FF)

    o_album_artist = ''
    for artist in album.artists:
        o_album_artist += artist.name
        if artist.join != '':
            o_album_artist += ' ' + artist.join + ' '

    '''
    o_album = album.title
    o_artist = o_album_artist
    o_artwork
    o_total_tracks = len(album.tracklist)
    o_year = album.released
    o_comment = 'Vinyl Rip'
    o_genre = album.genres[0]
    '''
    url = album.images[0]['uri']
    #urllib.request.urlretrieve(url,"albumart.jpg")
    #r = requests.get(url)
    #with open('albumart.jpg', 'wb') as albumfile:
    #    albumfile.write(r.content)

    try:
        opener = urllib.request.URLopener()
        opener.addheader('User-Agent', 'minty metadata automate')
        filename, headers = opener.retrieve(url, 'albumart.jpg')
    except:
        print("Failed to retrieve album art. Please download the following image and save it in the same folder as albumart.jpg")
        print(url)
        whocares = input("Press enter when done")

        

    for i in range(0,len(side_tracklist)):
        print('Tagging file ('+str(i+1) + '/' + str(len(side_tracklist)) + ')... ',end='')
        s = music_tag.load_file(str(i) + FE)
        track = side_tracklist[i]
        s['tracktitle'] = track.title
        s['album'] = album.title
        s['artist'] = o_album_artist
        s['albumartist'] = o_album_artist
        s['year'] = album.year
        s['genre'] = album.genres[0]
        s['tracknumber'] = first_track_no + i
        s['totaltracks'] = len(album.tracklist)
        with open('albumart.jpg','rb') as img_in:
            s['artwork'] = img_in.read()
        #s['artwork'].first.thumbnail([64,64])
        #s['artwork'].first.raw_thumbnail([64,64])
        s.save()


        # check varibale bit rate if ths doesn't fix it
        
        ffmpeg = (
            FFmpeg()
            .input(str(i) + FE)
            .output(str(first_track_no + i).zfill(2) + ' ' + track.title + ' - ' + o_album_artist + FE)
        )
        ffmpeg.execute()
        os.remove(str(i) + FE)
        print('Done.')
        
        
        #os.replace("reencode" + str(i) + FE,str(first_track_no + i).zfill(2) + ' ' + track.title + ' - ' + o_album_artist + FE)

def searchio():
    search_button.state(['disabled'])
    feedback.set("Searching, please wait warmly...")
    recordr.after(10,search_start)


def search_start(*args):
    global resulttext,resulthl,results,i,found,d
    query = search.get()
    token = tokenvar.get().strip()
    d = discogs_client.Client('mintyrecordmetadata/0.1', user_token=token)

    results = d.search(query,type='release',format='Vinyl')
    i = 0
    #print(len(results))
    found = False

    collection_text = ''
    resulttext = []
    resulthl = []
    recordr.after(10,search_continue)



def search_continue():
    global i,found,resulthl,resulttext
    collection_text = ''

    if i < len(results) and not (found and finish_early.get()):
        result = results[i]
        #print(result)
        if found == False:
            if len(d.identity().collection_items(result.id)) > 0:
                found = True
                collection_text = ' <<IN COLLECTION>>'
            else:
                collection_text = ' <<NOT FOUND>>'
        feedback.set("Progress: " + str(round( ((i+1) / len(results)) * 100 )) + "%")
        resulttext.append(str(i) + ' ==> ' + result.labels[0].catno + ': ' + result.artists[0].name + ' - ' + result.title + ' (' + result.country + ') - ' + result.formats[0]['name'] + collection_text)
        resulthl.append(result.id)
        #print(result.country)
        #print(result.formats[0]['name'])
        i += 1
        collection_text = ' <<UNCHECKED>>'
        recordr.after(10,search_continue)
    else:
        feedback.set("Search done")
        sresults['values'] = resulttext
        search_button.state(['!disabled'])

def hyperlink_update(*args):
    sresults.selection_clear()
    link_address.set("https://www.discogs.com/release/" + str(resulthl[resulttext.index(sresultvar.get())]))
    #https://www.discogs.com/release/
    result_link.bind("<Button-1>", lambda e: open_link(link_address.get()))

def open_link(url):
    webbrowser.open_new(url)

def file_browse():
    filename = filedialog.askopenfilename()
    filenamevar.set(filename)


with open("discogstoken2",'r') as token_file:
    token = token_file.read().strip()



recordr = Tk()
recordr.title("recordr")
uframe = ttk.Frame(recordr,padding="3 3 12 12")
uframe.grid(column=0,row=0,sticky=(N,W,E,S))
recordr.columnconfigure(0,weight=1)
recordr.columnconfigure(0,weight=1)


feedback = StringVar()
feedback.set("")

# discogs token
ttk.Label(uframe,text="Discogs token").grid(column=1,row=2,sticky=(W,E))
tokenvar = StringVar()
token_entry = ttk.Entry(uframe,width=40,textvariable=tokenvar)
token_entry.grid(column=2,row=2,sticky=(W,E))
tokenvar.set(token)

#search
ttk.Label(uframe,text="Search for Album or Release").grid(column=1,row=3,sticky=(W,E))
search = StringVar()
search_entry = ttk.Entry(uframe,width=40,textvariable=search)
search_entry.grid(column=2,row=3,sticky=(W,E))

#search row 2
finish_early = BooleanVar(value=True)
finish_early_check = ttk.Checkbutton(uframe,text="Stop searching when found",variable=finish_early)
finish_early_check.grid(column=1,row=4,sticky=(W,E))
search_button = ttk.Button(uframe,text="Search",command=searchio)
search_button.grid(column=2,row=4,sticky=(W,E))

#search results
sresultvar = StringVar()
sresults = ttk.Combobox(uframe,textvariable=sresultvar)
sresults.state(["readonly"])
sresults.grid(row=5,column=1,columnspan=3,sticky=(W,E))

sresults.bind('<<ComboboxSelected>>',hyperlink_update)


link_address = StringVar()
result_link = ttk.Label(uframe,textvariable=link_address,foreground="blue",cursor="hand2")
result_link.grid(row=6,column=1,columnspan=2,sticky=(W,E))



#divider
ttk.Separator(uframe,orient=HORIZONTAL).grid(row=10,column=1,columnspan=3,sticky=(W,E))

#file
ttk.Label(uframe,text="Recording file").grid(column=1,row=11,sticky=(W,E))
filenamevar = StringVar()
filename_entry = ttk.Entry(uframe,width=40,textvariable=filenamevar)
filename_entry.grid(column=1,row=12,columnspan=3,sticky=(W,E))

ttk.Button(uframe,text="Browse",command=file_browse).grid(row=11,column=2,columnspan=1,sticky=(W,E))



#divider
ttk.Separator(uframe,orient=HORIZONTAL).grid(row=20,column=1,columnspan=3,sticky=(W,E))

#progress
ttk.Label(uframe,textvariable=feedback).grid(column=1,row=21,columnspan=3,sticky=(W))






for child in uframe.winfo_children(): 
    child.grid_configure(padx=5, pady=5)

recordr.mainloop()





