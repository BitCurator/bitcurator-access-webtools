from flask import Flask, render_template, url_for, Response
import pytsk3
import os, sys, string, time, re
from mimetypes import MimeTypes

from dimac import app

image_list = []
file_list_root = []
dirDictList = [[]]

# FIXME: Imagedir is hardcoded for now. Will be moved to config file shortly
image_dir = "/home/bcadmin/disk_images"
num_images = 0

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
    global num_images
    num_images = len(image_list)

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
def root_directory_list(image_name, image_partition):
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
# Template rendering when a File is clicked
#
@app.route('/image/<image_name>/<image_partition>', defaults={'path': ''})
@app.route('/image/<image_name>/<image_partition>/<path:path>')

def file_clicked(image_name, image_partition, path):
    print("Files: Rendering Template for subdirectory or contents of a file: ",
          image_name, image_partition, path)
    
    image_index = dimacGetImageIndex(str(image_name), False)
    image_path = image_dir+'/'+image_name

    # A bit of an ugly string manipulation here: Since we are re-using
    # this flask route routine to get invoked by a browser-click on
    # any file/directory, the template code manipulates the "file" part
    # of the URL to replace "/" with "%", so flask can be cheated into
    # calling this routine (there is just one file name after the last
    # slash int he URL. This will be re-constructed in the end of this
    # routine to replace the % by '/' before calling render_template, so
    # appropriate HTML page will be rendered.


    # NO. FIXED NOW.
    file_name_list = path.split('/')
    file_name = file_name_list[len(file_name_list)-1]

    #file_path = re.sub('%','/',file_path)
    print "D: File_path after manipulation = ", path


    # To verify that the file_name exsits, we need the directory where
    # the file sits. That is if tje file name is $Extend/$RmData, we have
    # to look for the file $RmData under the directory $Extend. So we
    # will call the TSK API fs.open_dir with the parent directory
    # ($Extend in this example)
    temp_list = path.split("/")
    temp_list = file_name_list[0:(len(temp_list)-1)]
    parent_dir = '/'.join(temp_list)

    print("D: Invoking TSK API to get files under parent_dir: ", parent_dir)

    # Generate File_list for the parent directory to see if the
    dm = dimac()
    file_list, fs = dm.dimacGenFileList(image_path, image_index,
                                        int(image_partition), parent_dir)

    # Look for file_name in file_list
    for item in file_list:
        ## print("D: item-name={} file_name={} ".format(item['name'], file_name))
        if item['name'] == file_name:
            print("D : File {} Found in the list: ".format(file_name))
            break
    else:
        print("D: File_clicked: File {} not found in file_list".format(file_name))
            
    if item['isdir'] == True:
        # We will send the file_list under this directory to the template.
        # So calling once again the TSK API ipen_dir, with the current
        # directory, this time.
        file_list, fs = dm.dimacGenFileList(image_path, image_index,
                                        int(image_partition), path)


        # Generate the URL to communicate to the template:
        with app.test_request_context():
            url = url_for('file_clicked', image_name=str(image_name), image_partition=image_partition, path=path )

        print (">> Rendering template with URL: ", url)
        return render_template('fl_dir_temp_ext.html',
                   image_name=str(image_name),
                   partition_num=image_partition,
                   path=path,
                   file_list=file_list,
                   url=url)

    else:
        print("DDDDDDDDownloading File: ", item['name'])
        # It is an ordinary file
        f = fs.open_meta(inode=item['inode'])
    
        # Read data and store it in a string
        offset = 0
        size = f.info.meta.size
        BUFF_SIZE = 1024 * 1024

        total_data = ""
        while offset < size:
            available_to_read = min(BUFF_SIZE, size - offset)
            data = f.read_random(offset, available_to_read)
            if not data:
                print("Done with reading")
                break

            offset += len(data)
            total_data = total_data+data 
            print "LEN OF TOTAL DATA: ", len(total_data)
           
            #return data
            #results = generate_file_data()
        generator = (cell for row in total_data
                for cell in row)

        mime = MimeTypes()
        mime_type, a = mime.guess_type(file_name)
        print("MIME YTPE: ", mime_type)
        return Response(generator,
                       mimetype=mime_type,
                       headers={"Content-Disposition":
                                    "attachment;filename=file_name" })        
        '''
        return Response(generator,
                   mimetype="text/plain",
                   headers={"Content-Disposition":
                                "attachment;filename=file.txt" })        
        '''
        '''
        return render_template('fl_filecat_temp_ext.html',
        image_name=str(image_name),
        partition_num=image_partition,
        file_name=file_name,
        contents=str(data))
        #contents = data.decode("utf-8"))
        '''
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

                # First level files and directories off the root
                # Builds dirDictList (global) and returns file_list for
                # the root directory
                file_list_root = self.dimacListFiles(fs, "/", image_index, part.slot_num)
                ## print(file_list_root)
    
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

        file_list_root = self.dimacListFiles(fs, root_path, image_index, partition_num)

        return file_list_root, fs
        

    dimacFileInfo = ['name', 'size', 'mode', 'inode', 'p_inode', 'mtime', 'atime', 'ctime', 'isdir']


    def dimacListFiles(self, fs, path, image_index, partition_num):
        file_list = []
        print("Func:dimacListFiles: Listing Directory for PATH: ", path)
        directory = fs.open_dir(path=path)
        i=0
        for f in directory:
            is_dir = False
            '''
print("Func:dimacListFiles:root_path:{} size: {} inode: {} \
par inode: {} mode: {} type: {} ".format(f.info.name.name,\
f.info.meta.size, f.info.meta.addr, f.info.name.meta_addr,\
f.info.name.par_addr, f.info.meta.mode, f.info.meta.type))
'''
            if f.info.meta.type == 2:
                is_dir = True
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
