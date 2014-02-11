from flask import Flask, render_template
import pytsk3
import os, sys, string, time

app = Flask(__name__)

@app.route("/")

def bcBrowseImages():
    image_dir = "/home/bcadmin/disk_images" # HARDCODED: FIXME
    #for i in os.listdir(os.getcwd()):
    image_list = []
    for img in os.listdir(image_dir):
        if img.endswith(".E01") or i.endswith(".AFF"):
            print img
            image_list.append(img)

            # FIXME: The following routine is under construction
            bcGenerateHtmlForImage(image_dir+'/'+img)
            
        else:
            continue
    
    # Render the template for main page.
    print 'D: Image_list: ', image_list
    return render_template('fl_temp_ext.html', image_list=image_list)
    
part_array = ["image_path", "addr", "slot_num", "start_offset", "desc"]
partDictList = []
def bcGenerateHtmlForImage(image_path):
    num_partitions = 0
    img = pytsk3.Img_Info(image_path)
    volume = pytsk3.Volume_Info(img)
    partDictList = []
    for part in volume:
        # The slot_num field of volume object has a value of -1
        # for non-partition entries - like Unallocated partition
        # and Primary and extended tables. So we will look for this
        # field to be >=0 to count partitions with valid file systems
        if part.slot_num >= 0:
            num_partitions += 1

            # Add the entry to the List of dictionaries, partDictList.
            # The list will have one dictionary per partition. The image
            # name is added as the first element of each partition to 
            # avoid a two-dimentional list.
            ## print "D: image_path: ", image_path
            ## print "D: part_addr: ", part.addr
            ## print "D: part_slot_num: ", part.slot_num
            ## print "D: part_start_offset: ", part.start
            ## print "D: part_description: ", part.desc
            partDictList.append({part_array[0]:image_path, \
                                 part_array[1]:part.addr, \
                                 part_array[2]:part.slot_num, \
                                 part_array[3]:part.start, \
                                 part_array[4]:part.desc })

            # Open the file system for this image at the extracted 
            # start_offset.
            fs = pytsk3.FS_Info(img, offset=(part.start * 512))

            '''
            # Open the directory node based on the path
            directory = fs.open_dir(path="/")

            file_list = []
            # Iterate over all files in the directory
            for f in directory:
                if f.info.meta.type == 2:
                    print "File %s is a Directory" %f.info.name.name
                file_list.append(f.info.name.name)
            '''
            
    print "Number of Partitions = ", num_partitions
    

#def bcGetPartitionStart(image, partn):

#def bcGenerateHtmlForImage(image):
    



if __name__ == "__main__":
    app.run()
