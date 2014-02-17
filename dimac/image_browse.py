from flask import Flask, render_template
import pytsk3
import os, sys, string, time, re

from dimac import app

image_list = []
file_list_root = []
dirDictList = []
image_dir = "/home/bcadmin/disk_images" # HARDCODED: FIXME

@app.route("/")

def bcBrowseImages():
    global image_dir
    image_index = 0

    # Since image_list is declared globally, empty it before populating
    global image_list
    del image_list[:]
    for img in os.listdir(image_dir):
        if img.endswith(".E01") or img.endswith(".AFF"):
            print img
            global image_list
            image_list.append(img)

            dm = dimac()
            image_path = image_dir+'/'+img
            dm.num_partitions = dm.dimacGenerateHtmlForImage(image_path, image_index)
            image_index +=1
        else:
            continue
  
    # Render the template for main page.
    print 'D: Image_list: ', image_list
    return render_template('fl_temp_ext.html', image_list=image_list, np=dm.num_partitions)

def dimacGetImageIndex(image, is_path):
    global image_list
    if (is_path == True):
        image_name = os.path.basename(image_path)
    else:
        image_name = image
    global image_list
    for i in range(0, len(image_list)):
        if image_list[i] == image_name:
            return i
        continue
    else:
        print("Image not found in the list: ", image_name)

#
# Template rendering for Image Listing
#
@app.route('/image/<image_name>')
def image(image_name):
    print("Partitions: Rendering Template with partitions for img: ", image_name)
    num_partitions = dimac.num_partitions_ofimg[image_name]

    return render_template('fl_img_temp_ext.html', 
                            image_name=str(image_name), 
                            num_partitions=num_partitions)

#
# Template rendering for Directory Listing per partition 
#
@app.route('/image/<image_name>/<image_partition>')
def directory_list(image_name, image_partition):
    print("Files: Rendering Template with files for partition: ", 
                            image_name, image_partition)
    image_index = dimacGetImageIndex(str(image_name), False)
    dm = dimac()
    image_path = image_dir+'/'+image_name
    file_list_root, fs = dm.dimacGenFileList(image_path, image_index, 
                                             int(image_partition), '/')
    return render_template('fl_part_temp_ext.html', 
                           image_name=str(image_name), 
                           partition_num=image_partition, 
                           file_list=file_list_root)

#
# Template rendering for File CAT utility
#
@app.route('/image/<image_name>/<image_partition>/<file_path>')
def file_clicked(image_name, image_partition, file_path):
    print("Files: Rendering Template with contents of a file: ", 
          image_name, image_partition, file_path)
    
    image_index = dimacGetImageIndex(str(image_name), False)
    image_path = image_dir+'/'+image_name
    file_name = os.path.basename(file_path)
    file_path = '/'+file_path

    # First find out if it is a file or a directory.
    ##'''
    for dir_item in dirDictList:
        if dir_item['dirname'] == file_name:
            print("File found in dirDictList: ", file_name)
            
            break
        else:
            continue
    else:
        print("File %s could be a regular file. " %file_name)
    ##'''

    # For the files in the root directory, current directory is /. 
    # To reuse this func for other directories below the root,
    # This needs to be set appropriately. For now, this will do: FIXME.
    current_dir = "/"

    dm = dimac()
    file_list, fs = dm.dimacGenFileList(image_path, image_index, 
                                        int(image_partition), current_dir)

    # Look for file_name in file_list
    for item in file_list:
        if item['name'] == file_name:
            print("File Found in the list: ", file_name)
            
            if item['isdir'] == True:
                # It is a directory call the template to display file
                # list under this directory FIXME: Add template rendering
                # code for a directory: Can reuse the same templates used before
                for dir_item in dirDictList:
                    print dir_item

            else:
                f = fs.open_meta(inode=item['inode'])
            
                # Read data and store it in a string
                offset = 0
                size = f.info.meta.size
                BUFF_SIZE = 1024 * 1024

                while offset < size:
                    available_to_read = min(BUFF_SIZE, size - offset)
                    data = f.read_random(offset, available_to_read)
                    if not data: 
                        print("Done with reading")
                        break

                    offset += len(data)
                    #print data

                return render_template('fl_filecat_temp_ext.html', 
                            image_name=str(image_name), 
                            partition_num=image_partition, 
                            file_name=file_name,
                            contents=str(data))
                            #contents = data.decode("utf-8"))
class dimac:
    num_partitions = 0
    part_array = ["image_path", "addr", "slot_num", "start_offset", "desc"]
    partDictList = []
    num_partitions_ofimg = dict()

    def dimacGenerateHtmlForImage(self, image_path, image_index):
        img = pytsk3.Img_Info(image_path)
        volume = pytsk3.Volume_Info(img)
        self.partDictList.append([])
        for part in volume:
            # The slot_num field of volume object has a value of -1
            # for non-partition entries - like Unallocated partition
            # and Primary and extended tables. So we will look for this
            # field to be >=0 to count partitions with valid file systems
            if part.slot_num >= 0:
                self.num_partitions += 1

                # Add the entry to the List of dictionaries, partDictList.
                # The list will have one dictionary per partition. The image
                # name is added as the first element of each partition to 
                # avoid a two-dimentional list.
                print "D: image_path: ", image_path
                print "D: part_addr: ", part.addr
                print "D: part_slot_num: ", part.slot_num
                print "D: part_start_offset: ", part.start
                print "D: part_description: ", part.desc
                self.partDictList[image_index].append({self.part_array[0]:image_path, \
                                     self.part_array[1]:part.addr, \
                                     self.part_array[2]:part.slot_num, \
                                     self.part_array[3]:part.start, \
                                     self.part_array[4]:part.desc })
    
                # Open the file system for this image at the extracted 
                # start_offset.
                fs = pytsk3.FS_Info(img, offset=(part.start * 512))

                file_list_root = self.dimacListFiles(fs, "/")
                print(file_list_root) 
    
                '''
                # Open the directory node based on the path
                directory = fs.open_dir(path="/")
    
                file_list[image = []
                num_dirs = 0
                # Iterate over all files in the directory
                for f in directory:
                    if f.info.meta.type == 2:
                        num_dirs += 1
                        ## print "File %s is a Directory" %f.info.name.name
                    file_list.append(f.info.name.name)
                
                ## print "Number of directoriues: ", num_dirs
                print file_list
                '''
        image_name = os.path.basename(image_path)
        self.num_partitions_ofimg[image_name] = self.num_partitions
        ## print ("D: Number of Partitions for image = ", image_name, self.num_partitions)
        return (self.num_partitions)

    def dimacGenFileList(self, image_path, image_index, partition_num, root_path):
        img = pytsk3.Img_Info(image_path)
        # Get the start of the partition:
        part_start = self.partDictList[int(image_index)][partition_num-1]['start_offset']

        # Open the file system for this image at the extracted 
        # start_offset.
        fs = pytsk3.FS_Info(img, offset=(part_start * 512))

        file_list_root = self.dimacListFiles(fs, root_path)

        return file_list_root, fs
        

    dimacFileInfo = ['name', 'size', 'mode', 'inode', 'p_inode', 'mtime', 'atime', 'ctime', 'isdir']
    dimacDirInfo = ['dirname', 'inode', 'par_inode', 'dirpath']

    def dimacListFiles(self, fs, path):
        file_list = []
        directory = fs.open_dir(path=path)
        i=0
        print("Listing Directory for PATH: ", path)
        for f in directory:
            is_dir = False
            ## print D: f.info.name.name, f.info.meta.size, f.info.meta.addr, f.info.name.meta_addr, f.info.name.par_addr, f.info.meta.mode, f.info.meta.type
            if f.info.meta.type == 2:
                is_dir = True

                # Append the inode and parent's inode to dirDictList
                global dirDictList
                dirDictList.append({self.dimacDirInfo[0]:re.escape(f.info.name.name), \
                              self.dimacDirInfo[1]:f.info.meta.addr, \
                              self.dimacDirInfo[2]:f.info.name.par_addr, \
                              self.dimacDirInfo[3]:path })       

            file_list.append({self.dimacFileInfo[0]:f.info.name.name, \
                              self.dimacFileInfo[1]:f.info.meta.size, \
                              self.dimacFileInfo[2]:f.info.meta.mode, \
                              self.dimacFileInfo[3]:f.info.meta.addr, \
                              self.dimacFileInfo[4]:f.info.name.par_addr, \
                              self.dimacFileInfo[5]:f.info.meta.mtime, \
                              self.dimacFileInfo[6]:f.info.meta.atime, \
                              self.dimacFileInfo[7]:f.info.meta.ctime, \
                              self.dimacFileInfo[8]:is_dir })

        return file_list

    

if __name__ == "__main__":
    dm = dimac()
    app.run()
