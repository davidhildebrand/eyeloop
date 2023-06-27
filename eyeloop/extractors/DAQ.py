import eyeloop.config as config
# import json
import logging
import nidaqmx
import numpy as np
from pathlib import Path

import matplotlib.pyplot as plt
logging.getLogger(name='matplotlib').setLevel(logging.WARNING) #main logging is set to DEBUG mode

class DAQ_extractor:
    def __init__(self):
        #self.output_dir = output_dir
        #self.datalog_path = Path(output_dir, f"datalog.json")
        #self.file = open(self.datalog_path, "a")

        self.voltage_gain = 1.0

        self.tracking_started = False
        self.recording_baseline = False
        self.first_run = True

        self.gui_centering_button_press = False

        self.pupil_XY_task = nidaqmx.Task()
        self.pupil_area_task = nidaqmx.Task()
        self.pupil_XY_task.ao_channels.add_ao_voltage_chan("MarmoEye_XY_USB6001/ao0:1", max_val=10, min_val=-10)
        
        self.output_pupil_size = True
        try:
            if self.output_pupil_size:
                self.pupil_area_task.ao_channels.add_ao_voltage_chan("MarmoEye_area_USB6001/ao0:1", max_val=10, min_val=-10)
        except:
            self.output_pupil_size = False
            print('MarmoEye_area_USB6001 not connected, will not output pupil area and binary')

    def activate(self):
        
        plt.close(self.plot.fig)
        delattr(self, 'plot')
        # self.file.write(json.dumps('Experiment started') + "\n")
        # self.file.write(json.dumps('Parameters: ') + "\n")
        # self.file.write(json.dumps(config.engine.subject_parameters, indent = 4))
        self.tracking_started = True
        return

    def fetch(self, core):
        self.core = core
        try:
            pupil_coords = self.core.dataout["pupil"][0]
            config.engine.last_pupil_coords = pupil_coords
            pupil_x_volts = ((pupil_coords[0] - self.center_x_pix) * config.engine.subject_parameters["voltage_gain"] / 100) * 10 # One hundred pixels up should be +10V at gain = 1
            # The pupil_y pixel coordinate increases from top-to-bottom of the image. We'll flip the sign of the voltage
            pupil_y_volts = ((self.center_y_pix - pupil_coords[1]) * config.engine.subject_parameters["voltage_gain"] / 100) * 10 # One hundred pixels up should be +10V at gain = 1
            pupil_area_volts = (self.core.dataout["pupil"][1] + self.core.dataout["pupil"][2]) / 2 / 100 * 20 - 10 # Radius of 100 pixels is 10 V.
            pupil_x_volts = np.clip(pupil_x_volts, -10, 10)
            pupil_y_volts = np.clip(pupil_y_volts, -10, 10)
            pupil_area_volts = np.clip(pupil_area_volts, -10, 10)
            pupil_detected_volts = 5
        except:
            [pupil_x_volts,pupil_y_volts] = [-10,-10]
            pupil_area_volts = -10
            pupil_detected_volts = -5

        self.pupil_XY_task.write([pupil_x_volts,pupil_y_volts])
        if self.output_pupil_size:
            self.pupil_area_task.write([pupil_area_volts,pupil_detected_volts])

        # try:
        #     if config.engine.scope_started:
        #         self.file.write(json.dumps(core.dataout) + "\n")
        # except ValueError:
        #     pass
        
        if self.tracking_started == False:

            ## Plotting in real time during calibration
            if self.first_run:
                self.plot = type('', (), {})() # create empty object
                self.plot.x, self.plot.y = [pupil_x_volts] * 40, [pupil_y_volts] * 40
                self.plot.fig, self.plot.ax = plt.subplots()
                (self.plot.ln,) = self.plot.ax.plot(self.plot.x, self.plot.y, animated=True)
                fig_manager = plt.get_current_fig_manager()
                fig_manager.window.setGeometry(750, 50, 500, 500)#(left, top, width, height)
                plt.xlim([-10.5, 10.5])
                plt.ylim([-10.5, 10.5])
                plt.show(block=False)
                plt.pause(0.05)
                self.plot.bg = self.plot.fig.canvas.copy_from_bbox(self.plot.fig.bbox)
                self.plot.ax.draw_artist(self.plot.ln)
                self.plot.fig.canvas.blit(self.plot.fig.bbox)
                self.first_run = False

            self.plot.x.append(pupil_x_volts)
            self.plot.y.append(pupil_y_volts)
            self.plot.x = self.plot.x[-40:]
            self.plot.y = self.plot.y[-40:]
            self.plot.fig.canvas.restore_region(self.plot.bg)
            self.plot.ln.set_data(self.plot.x,self.plot.y)
            self.plot.ax.draw_artist(self.plot.ln)
            self.plot.fig.canvas.blit(self.plot.fig.bbox)
            self.plot.fig.canvas.flush_events()

            if pupil_x_volts != -10 and pupil_y_volts != -10:
                if self.gui_centering_button_press:
                    self.recording_baseline = not self.recording_baseline

                    if self.recording_baseline: # If starting recording, clear previous x,y values
                        self.previous_pupil_x_pixs = []
                        self.previous_pupil_y_pixs = []
                        print('Started gaze recording for centering voltage')
                    else: # If stopping recording, calculate center from previous x,y values
                        self.center_x_pix = np.median(self.previous_pupil_x_pixs) 
                        self.center_y_pix = np.median(self.previous_pupil_y_pixs)
                        try:
                            config.engine.subject_parameters["center_x_pix"] = self.center_x_pix
                            config.engine.subject_parameters["center_y_pix"] = self.center_y_pix
                            if config.engine.adjusting_ROI:
                                config.engine.candidate_ROI["OffsetX"] = 8 * round((self.center_x_pix - config.engine.subject_parameters["Width"] /2) / 8) 
                                config.engine.candidate_ROI["OffsetY"] = 2 * round((self.center_y_pix - config.engine.subject_parameters["Height"]/2) / 2) 
                                config.engine.candidate_ROI["Width"] = config.engine.subject_parameters["Width"]
                                config.engine.candidate_ROI["Height"] = config.engine.subject_parameters["Height"]
                        except Exception as e:
                            print(e)
                        print('Finished gaze recording for centering voltage')
                        print('center_x_pix = ' + str(self.center_x_pix))
                        print('center_y_pix = ' + str(self.center_y_pix))

                    self.gui_centering_button_press = False

                if self.recording_baseline:
                    self.previous_pupil_x_pixs.append(pupil_coords[0])
                    self.previous_pupil_y_pixs.append(pupil_coords[1])

    def release(self, core):
        # try:
        #     self.file.write(json.dumps(core.dataout) + "\n")
        #     self.file.close()
        # except ValueError:
        #     pass
        self.fetch(core)
        #return
        #logging.debug("DAQ_extractor.release() called")

    # def set_digital_line(channel, value):
    # digital_output = PyDAQmx.Task()
    # digital_output.CreateDOChan(channel,'do', DAQmxConstants.DAQmx_Val_ChanPerLine)
    # digital_output.WriteDigitalLines(1,
    #                                 True,
    #                                 1.0,
    #                                 DAQmxConstants.DAQmx_Val_GroupByChannel,
    #                                 numpy.array([int(value)], dtype=numpy.uint8),
    #                                 None,
    #                                 None)
    # digital_output.ClearTask()
