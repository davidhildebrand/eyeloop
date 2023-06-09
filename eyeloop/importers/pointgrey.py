import cv2
import eyeloop.config as config
from eyeloop.importers.importer import IMPORTER
import glob
import numpy as np
import PySpin
import tkinter as tk
import nidaqmx
from copy import deepcopy

class Importer(IMPORTER):

    def first_frame(self) -> None:
        # load first frame
        self.setup_camera()
        image_result = self.cam.GetNextImage()
        image = image_result.GetNDArray()
        height, width = image.shape
        print('Image shape: '+ str(image.shape))
        self.arm(width, height, image)
        self.experiment_started = False

        # Task for counting acquisition frames via a counter input
        self.frame_counter_scope = 0
        acqcount_src = 'MarmoEye_XY_USB6001/ctr0'
        acqcount_line = '/MarmoEye_XY_USB6001/PFI0'
        self.acqcount_task = nidaqmx.Task()
        self.acqcount_task.ci_channels.add_ci_count_edges_chan(counter=acqcount_src)
        self.acqcount_chan = self.acqcount_task.ci_channels[acqcount_src]
        self.acqcount_chan.ci_count_edges_active_edge = nidaqmx.constants.Edge.RISING
        self.acqcount_chan.ci_count_edges_initial_cnt = 0
        self.acqcount_chan.ci_count_edges_dir = nidaqmx.constants.CountDirection.COUNT_UP
        self.acqcount_chan.ci_count_edges_term = acqcount_line

    def route(self) -> None:
        self.first_frame()
        while True:
            image_result = self.cam.GetNextImage()
            image = image_result.GetNDArray()
            image_result.Release()
            config.engine.iterate(image)
            self.frame += 1 
            if self.experiment_started and config.engine.save_images:
                self.frame_counter_scope = self.acqcount_task.read()
                quotient_256x256, remainder_256x256 = divmod(self.frame_counter_scope, 65536)
                quotient_256, remainder_256 = divmod(remainder_256x256, 256)
                image_for_saving = deepcopy(image)

                # Using a 3x3 pix array in the top left for simplicity and peace of mind...
                image_for_saving[:3,:3] = remainder_256
                image_for_saving[:2,:2] = quotient_256
                image_for_saving[:1,:1] = quotient_256x256
                
                self.save(image_for_saving)

                # You can recover the frame counter with this:
                #calculated_frame_scope = 256 * 256 * quotient_256x256 + 256 * quotient_256 + remainder_256

    def activate(self) -> None:
        self.experiment_started = True
        self.frame = 0
        self.acqcount_task.start()

    def release(self) -> None:
        self.cam.EndAcquisition()
        self.cam.DeInit()
        del self.cam
        self.system.ReleaseInstance()

    def setup_camera(self) -> None:
        # Retrieve singleton reference to system object
        self.system = PySpin.System.GetInstance()
        
        # Retrieve list of cameras from the system
        cam_list = self.system.GetCameras()
        num_cameras = cam_list.GetSize()
        print('Number of cameras detected: %d' % num_cameras)
        
        # Finish if there are no cameras
        if num_cameras == 0:
            # Clear camera list before releasing system
            cam_list.Clear()
            # Release system instance
            system.ReleaseInstance()
            print('Not enough cameras!')
            input('Done! Press Enter to exit...')
        
        # Setting up first detected camera
        self.cam = cam_list[0]
        nodemap_tldevice = self.cam.GetTLDeviceNodeMap()
        self.cam.Init()
        nodemap = self.cam.GetNodeMap()

        ## Setting image format to mono8 - from ImageFormatControl.py example
        node_pixel_format = PySpin.CEnumerationPtr(nodemap.GetNode('PixelFormat'))
        if PySpin.IsAvailable(node_pixel_format) and PySpin.IsWritable(node_pixel_format):
            # Retrieve the desired entry node from the enumeration node
            node_pixel_format_mono8 = PySpin.CEnumEntryPtr(node_pixel_format.GetEntryByName('Mono8'))
            if PySpin.IsAvailable(node_pixel_format_mono8) and PySpin.IsReadable(node_pixel_format_mono8):
                # Retrieve the integer value from the entry node
                pixel_format_mono8 = node_pixel_format_mono8.GetValue()
                # Set integer as new value for enumeration node
                node_pixel_format.SetIntValue(pixel_format_mono8)
                print('Pixel format set to %s...' % node_pixel_format.GetCurrentEntry().GetSymbolic())
            else:
                print('Pixel format mono 8 not available...')
        else:
            print('Pixel format not available...')

        ## Reset camera ROI and apply appropiate settings for this subject
        
        node_offset_x = PySpin.CIntegerPtr(nodemap.GetNode("OffsetX"))
        node_offset_x.SetValue(0) # If not set to 0, this affects maximum width/height

        node_offset_y = PySpin.CIntegerPtr(nodemap.GetNode("OffsetY"))
        node_offset_y.SetValue(0) # If not set to 0, this affects maximum width/height

        node_width = PySpin.CIntegerPtr(nodemap.GetNode("Width"))
        max_width = node_width.GetMax()

        node_height = PySpin.CIntegerPtr(nodemap.GetNode("Height"))
        max_height = node_height.GetMax()

        search_string = str(config.file_manager.output_root) + "/Parameters_*.npy"
        parameter_files = glob.glob(search_string)
        names_available_parameters = []
        available_parameters = []
        for i in range(len(parameter_files)):
            parameters = np.load(parameter_files[i], allow_pickle = True)
            parameters = parameters.item()
            available_parameters.append(parameters)
            names_available_parameters.append(parameters['Name'])
            
        fullFOV_parameters = {'Name' : 'FullFOV', 'Width' : max_width, 'Height' : max_height, 
        'OffsetX' : 0, 'OffsetY' : 0, "center_x_pix" : max_width/2, "center_y_pix" : max_height/2,
        "voltage_gain" : 1, "p_binarythreshold" : 100, "p_blur" : 5, "min_radius" : 10, "max_radius" : 100,
        "lower_lim_std" : -0.3, "upper_lim_std" : 3.5}

        fullFOV_Right_parameters = {'Name' : 'FullFOV_Right', 'Width' : max_width-256, 'Height' : max_height, 
        'OffsetX' : 256, 'OffsetY' : 0, "center_x_pix" : max_width/2, "center_y_pix" : max_height/2,
        "voltage_gain" : 1, "p_binarythreshold" : 100, "p_blur" : 5, "min_radius" : 10, "max_radius" : 100,
        "lower_lim_std" : -0.3, "upper_lim_std" : 3.5}
        
        available_parameters.append(fullFOV_parameters)
        available_parameters.append(fullFOV_Right_parameters)
        names_available_parameters.append(fullFOV_parameters['Name'])
        names_available_parameters.append(fullFOV_Right_parameters['Name'])

        window_main = tk.Tk(className='Select subject')
        window_main.geometry('200x200')
        
        listbox_1 = tk.Listbox(window_main, selectmode=tk.EXTENDED)
        for s in range(len(names_available_parameters)):
            listbox_1.insert(s+1, names_available_parameters[s])
        listbox_1.pack()
        
        def submitFunction():
            global selection
            selection = listbox_1.curselection()
            selection = selection[0]
            window_main.destroy()
        
        submit = tk.Button(window_main, text='Submit', command=submitFunction)
        submit.pack()
        window_main.mainloop()

        subject_parameters = available_parameters[selection]
        print('subject_parameters')
        print(subject_parameters)
        ## Modify Width/Height/OffsetX/OffsetY
        node_width.SetValue(subject_parameters['Width'])
        node_height.SetValue(subject_parameters['Height'])
        node_offset_x.SetValue(subject_parameters['OffsetX'])
        node_offset_y.SetValue(subject_parameters['OffsetY'])
        config.engine.subject_parameters = subject_parameters

        ## Get frame rate - from SaveToAvi.py example
        node_acquisition_framerate = PySpin.CFloatPtr(nodemap.GetNode('AcquisitionFrameRate'))
        framerate_to_set = node_acquisition_framerate.GetValue()
        print('Camera frame rate %d...' % framerate_to_set)

        # Change bufferhandling mode to NewestOnly
        sNodemap = self.cam.GetTLStreamNodeMap()
        node_bufferhandling_mode = PySpin.CEnumerationPtr(sNodemap.GetNode('StreamBufferHandlingMode'))
        if not PySpin.IsAvailable(node_bufferhandling_mode) or not PySpin.IsWritable(node_bufferhandling_mode):
            print('Unable to set stream buffer handling mode.. Aborting...')
        
        # Retrieve entry node from enumeration node
        node_newestonly = node_bufferhandling_mode.GetEntryByName('NewestOnly')
        if not PySpin.IsAvailable(node_newestonly) or not PySpin.IsReadable(node_newestonly):
            print('Unable to set stream buffer handling mode.. Aborting...')
        
        # Retrieve integer value from entry node
        node_newestonly_mode = node_newestonly.GetValue()
        
        # Set integer value from entry node as new value of enumeration node
        node_bufferhandling_mode.SetIntValue(node_newestonly_mode)
        
        try:
            node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
            if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
                print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
        
            # Retrieve entry node from enumeration node
            node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
            if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(
                    node_acquisition_mode_continuous):
                print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
        
            # Retrieve integer value from entry node
            acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
        
            # Set integer value from entry node as new value of enumeration node
            node_acquisition_mode.SetIntValue(acquisition_mode_continuous)
        
            self.cam.BeginAcquisition()
        
            print('Acquiring images...')
            device_serial_number = ''
            node_device_serial_number = PySpin.CStringPtr(nodemap_tldevice.GetNode('DeviceSerialNumber'))
            if PySpin.IsAvailable(node_device_serial_number) and PySpin.IsReadable(node_device_serial_number):
                device_serial_number = node_device_serial_number.GetValue()
                print('Device serial number retrieved as %s...' % device_serial_number)
        
        except PySpin.SpinnakerException as ex:
            print('Error: %s' % ex)

