import os
from pathlib import Path
import numpy as np
import eyeloop.config as config
from eyeloop.constants.minimum_gui_constants import *
from eyeloop.utilities.general_operations import to_int, tuple_int
import threading
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
import logging
logger = logging.getLogger(__name__)

class GUI:
    def __init__(self) -> None:
        dir_path = os.path.dirname(os.path.realpath(__file__))

        self.terminate = -1
        self.update = self.adj_update#real_update
        self.skip = 0
        self.first_run = True

        self.pupil_ = lambda _: False

    def tip_mousecallback(self, event, x: int, y: int, flags, params) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            if 10 < y < 35:
                if 20 < x < 209:
                    x -= 27
                    x = int(x / 36) + 1

    def mousecallback(self, event, x, y, flags, params) -> None:
        x = x % self.width
        self.cursor = (x, y)

    def release(self):
        #self.out.release()
        cv2.destroyAllWindows()

    def remove_mousecallback(self) -> None:
        cv2.setMouseCallback("CONFIGURATION", lambda *args: None)

    def key_listener(self, key: int) -> None:
        try:
            key = chr(key)
        except:
            return

        if "q" == key:
            # Terminate tracking
            print("Exiting.")
            config.engine.release()

        if "1" == key:
            try:
                self.pupil_processor.reset(self.cursor)
                self.pupil_ = self.pupil
                print("Pupil selected.")

                if 'FullFOV' in config.engine.subject_parameters["Name"]:
                    self.plot.sWidth.set_val(int(192))
                    self.plot.sHeight.set_val(int(192))
                    self.plot.sOffsetX.set_val(int(round((self.cursor[0] - 192/2)/8) * 8))
                    self.plot.sOffsetY.set_val(int(round((self.cursor[1] - 192/2)/2) * 2))
                    
            except Exception as e:
                logger.info(f"pupil selection failed; {e}")


    def arm(self, width: int, height: int) -> None:
        self.fps = np.round(1/config.arguments.fps, 2)

        self.pupil_processor = config.engine.pupil_processor

        self.cr_index = 0
        self.current_cr_processor = config.engine.cr_processor_1  # primary corneal reflection
        #self.cr_processor_1 = config.engine.cr_processor_1
        #self.cr_processor_2 = config.engine.cr_processor_2

        self.width, self.height = width, height
        self.binary_width = max(width, 300)
        self.binary_height = max(height, 200)

        self.bin_stock = np.zeros((self.binary_height, self.binary_width))
        self.bin_P = self.bin_stock.copy()
        self.bin_CR = self.bin_stock.copy()

        self.src_txt = np.zeros((20, width, 3))
        self.prev_txt = self.src_txt.copy()
        cv2.putText(self.src_txt, 'Source', (15, 12), font, .7, (255, 255, 255), 0, cv2.LINE_4)
        cv2.putText(self.prev_txt, 'Preview', (15, 12), font, .7, (255, 255, 255), 0, cv2.LINE_4)
        cv2.putText(self.prev_txt, 'EyeLoop', (width - 50, 12), font, .5, (255, 255, 255), 0, cv2.LINE_8)

        self.bin_stock_txt = np.zeros((20, self.binary_width))
        self.bin_stock_txt_selected = self.bin_stock_txt.copy()
        self.crstock_txt = self.bin_stock_txt.copy()
        self.crstock_txt[0:1, 0:self.binary_width] = 1
        self.crstock_txt_selected = self.crstock_txt.copy()

        cv2.imshow("CONFIGURATION", np.hstack((self.bin_stock, self.bin_stock)))
        cv2.imshow("BINARY", np.vstack((self.bin_stock, self.bin_stock)))

        cv2.moveWindow("CONFIGURATION", 50, 20)
        if height < 600:
            cv2.moveWindow("BINARY", 50, 50 + height)
        else:
            cv2.moveWindow("BINARY", 50, 300)

        try:
            cv2.setMouseCallback("CONFIGURATION", self.mousecallback)
        except:
            print("Could not bind mouse-buttons.")

        ### GUI with parameters and live voltage outputs
        self.plot = type('', (), {})() # create empty object
        self.plot.x, self.plot.y = [0] * 40, [0] * 40
        self.plot.fig, self.plot.ax = plt.subplots()
        plt.axis('off')

        axcolor = 'lightgoldenrodyellow'

        axbinarythreshold = plt.axes([0.25, 0.96, 0.65, 0.03], facecolor=axcolor)
        axblur = plt.axes([0.25, 0.92, 0.65, 0.03], facecolor=axcolor)
        axmin_radius = plt.axes([0.25, 0.88, 0.65, 0.03], facecolor=axcolor)
        axmax_radius = plt.axes([0.25, 0.84, 0.65, 0.03], facecolor=axcolor)
        axgain = plt.axes([0.25, 0.80, 0.65, 0.03], facecolor=axcolor)
        axWidth = plt.axes([0.25, 0.76, 0.65, 0.03], facecolor=axcolor)
        axHeight = plt.axes([0.25, 0.72, 0.65, 0.03], facecolor=axcolor)
        axOffsetX = plt.axes([0.25, 0.68, 0.65, 0.03], facecolor=axcolor)
        axOffsetY = plt.axes([0.25, 0.64, 0.65, 0.03], facecolor=axcolor)
        axlower_lim_std = plt.axes([0.25, 0.60, 0.65, 0.03], facecolor=axcolor)
        axupper_lim_std = plt.axes([0.25, 0.56, 0.65, 0.03], facecolor=axcolor)
        
        sbinarythreshold =  Slider(axbinarythreshold, 'BinThresh', 1, 200, valinit=config.engine.subject_parameters["p_binarythreshold"],valstep=1)
        sblur = Slider(axblur, 'Blur', 1, 49, valinit= config.engine.subject_parameters["p_blur"], valstep=2)
        smin_radius = Slider(axmin_radius, 'MinRadius', 1, 300, valinit=config.engine.subject_parameters["min_radius"], valstep=1)
        smax_radius = Slider(axmax_radius, 'MaxRadius', 1, 300, valinit=config.engine.subject_parameters["max_radius"], valstep=1)
        sgain = Slider(axgain, 'VoltageGain(' + str(round(config.engine.subject_parameters["voltage_gain"],2)) + ')', 1, 20, valinit=config.engine.subject_parameters["voltage_gain"], valstep=0.1)
        sWidth = Slider(axWidth, 'ROIWidth(' + str(config.engine.subject_parameters["Width"]) + ')', 16, 800, valinit=config.engine.subject_parameters["Width"], valstep=16)
        sHeight = Slider(axHeight, 'ROIHeight(' + str(config.engine.subject_parameters["Height"]) + ')', 16, 600, valinit=config.engine.subject_parameters["Height"], valstep=4)
        sOffsetX = Slider(axOffsetX, 'OffsetX(' + str(config.engine.subject_parameters["OffsetX"]) + ')', 0, 1000, valinit=config.engine.subject_parameters["OffsetX"], valstep=8)
        sOffsetY = Slider(axOffsetY, 'OffsetY(' + str(config.engine.subject_parameters["OffsetY"]) + ')', 0, 1000, valinit=config.engine.subject_parameters["OffsetY"], valstep=2)
        slower_lim_std = Slider(axlower_lim_std, 'lower_lim_std(' + str(round(config.engine.subject_parameters["lower_lim_std"],2)) + ')', -5, 5, valinit=config.engine.subject_parameters["lower_lim_std"], valstep=0.1)
        supper_lim_std = Slider(axupper_lim_std, 'upper_lim_std(' + str(round(config.engine.subject_parameters["upper_lim_std"],2)) + ')', -5, 5, valinit=config.engine.subject_parameters["upper_lim_std"], valstep=0.1)
        
        def update(val):
            config.engine.subject_parameters["p_binarythreshold"] = sbinarythreshold.val
            config.engine.subject_parameters["p_blur"] = sblur.val
            config.engine.subject_parameters["min_radius"] = smin_radius.val
            config.engine.subject_parameters["max_radius"] = smax_radius.val
            config.engine.subject_parameters["voltage_gain"] = sgain.val
            config.engine.subject_parameters["Width"] = sWidth.val
            config.engine.subject_parameters["Height"] = sHeight.val
            config.engine.subject_parameters["OffsetX"] = sOffsetX.val
            config.engine.subject_parameters["OffsetY"] = sOffsetY.val
            config.engine.subject_parameters["lower_lim_std"] = slower_lim_std.val
            config.engine.subject_parameters["upper_lim_std"] = supper_lim_std.val
            
        sbinarythreshold.on_changed(update)
        sblur.on_changed(update)
        smin_radius.on_changed(update)
        smax_radius.on_changed(update)
        sgain.on_changed(update)
        sHeight.on_changed(update)
        sWidth.on_changed(update)
        sOffsetX.on_changed(update)
        sOffsetY.on_changed(update)
        slower_lim_std.on_changed(update)
        supper_lim_std.on_changed(update)

        def reset():
            sbinarythreshold.reset()
            sblur.reset()
            smin_radius.reset()
            smax_radius.reset()
            sgain.reset()
            sHeight.reset()
            sWidth.reset()
            sOffsetX.reset()
            sOffsetY.reset()
            slower_lim_std.reset()
            supper_lim_std.reset()
            
        resetax = plt.axes([0.6, 0.025, 0.25, 0.04])
        button1 = Button(resetax, 'Reset', color=axcolor, hovercolor='0.975')

        def reset1(event):
            reset()
        button1.on_clicked(reset1)

        resetax2 = plt.axes([0.6, 0.075, 0.25, 0.04])
        button2 = Button(resetax2, 'Switch Algorithm', color=axcolor, hovercolor='0.975')
        def reset2(event):
            self.pupil_processor.convex_hull = not self.pupil_processor.convex_hull
            print("Filling holes in pupil processor: " + str(self.pupil_processor.convex_hull))
        button2.on_clicked(reset2)
        
        resetax3 = plt.axes([0.6, 0.125, 0.25, 0.04])
        button3 = Button(resetax3, 'Start!', color=axcolor, hovercolor='0.975')
        def reset3(event):
            print("Initiating tracking..")
            
            plt.close(self.plot.fig)
            delattr(self, 'plot')
            plt.close('all')
            self.remove_mousecallback()
            cv2.destroyWindow("CONFIGURATION")
            cv2.destroyWindow("BINARY")
            cv2.imshow("TRACKING", self.bin_stock)
            cv2.moveWindow("TRACKING", 50, 50)
            self.update = self.real_update
            config.engine.activate()
        button3.on_clicked(reset3)

        resetax4 = plt.axes([0.6, 0.175, 0.25, 0.04])
        button4 = Button(resetax4, 'Save and Quit', color=axcolor, hovercolor='0.975')
        def reset4(event):
            config.engine.release()
        button4.on_clicked(reset4)

        resetax5 = plt.axes([0.6, 0.225, 0.25, 0.04])
        button5 = Button(resetax5, 'Reset and Quit', color=axcolor, hovercolor='0.975')
        def reset5(event):
            reset()
            config.engine.release()
        button5.on_clicked(reset5)

        resetax6 = plt.axes([0.6, 0.275, 0.25, 0.04])
        button6 = Button(resetax6, 'Start Center', color=axcolor, hovercolor='0.975')
        def reset6(event):
            config.engine.extractors[1].x_key_detected = True #extractors[1] corresponds to DAQ_extractor
            if config.engine.extractors[1].recording_baseline == False:
                button6.label.set_text('Centering...')
                print('Centering...')
            else:
                button6.label.set_text('Start Center')
                print('Centered')
        button6.on_clicked(reset6)

        resetax7 = plt.axes([0.6, 0.325, 0.25, 0.04])
        if config.engine.save_images:
            button7 = Button(resetax7, 'Save Images = On', color=axcolor, hovercolor='0.975')
        else:
            button7 = Button(resetax7, 'Save Images = Off', color=axcolor, hovercolor='0.975')
        def reset7(event):
            config.engine.save_images = not config.engine.save_images
            print('Save images set to: ' + str(config.engine.save_images))
            if config.engine.save_images:
                button7.label.set_text('Save Images = On')
            else:
                button7.label.set_text('Save Images = Off')
        button7.on_clicked(reset7)

        self.plot.ax2 = plt.axes([0.06, 0.05, 0.5, 0.5])
        (self.plot.ln,) = self.plot.ax2.plot(self.plot.x, self.plot.y, animated=True)
        plt.xlim([-10.5, 10.5])
        plt.ylim([-10.5, 10.5])

        plt.show(block=False)
        plt.pause(0.05)

        self.plot.bg = self.plot.fig.canvas.copy_from_bbox(self.plot.ax2.bbox)
        self.plot.ax2.draw_artist(self.plot.ln)
        self.plot.fig.canvas.blit(self.plot.fig.bbox)

        self.plot.button1 = button1 #otherwise, buttons are gone
        self.plot.button2 = button2
        self.plot.button3 = button3
        self.plot.button4 = button4
        self.plot.button5 = button5
        self.plot.button6 = button6
        self.plot.button7 = button7
        self.plot.sWidth = sWidth #this sliders are modified when creating a new subject_parameters from FullFOV
        self.plot.sHeight = sHeight
        self.plot.sOffsetX = sOffsetX
        self.plot.sOffsetY = sOffsetY

    def place_cross(self, source: np.ndarray, point: tuple, color: tuple) -> None:
        try:
            source[to_int(point[1] - 3):to_int(point[1] + 4), to_int(point[0])] = color
            source[to_int(point[1]), to_int(point[0] - 3):to_int(point[0] + 4)] = color
        except:
            pass
    
    def place_square(self, source: np.ndarray, offsets_xy: tuple, size_xy: tuple, color: tuple) -> None:
        # offsets_xy should be the [left,top] coordinates
        try:
            source[to_int(offsets_xy[1]),               to_int(offsets_xy[0]):to_int(offsets_xy[0] + size_xy[0])] = color
            source[to_int(offsets_xy[1] + size_xy[1]),  to_int(offsets_xy[0]):to_int(offsets_xy[0] + size_xy[0])] = color
            source[to_int(offsets_xy[1]):to_int(offsets_xy[1] + size_xy[1]), to_int(offsets_xy[0])] = color
            source[to_int(offsets_xy[1]):to_int(offsets_xy[1] + size_xy[1]), to_int(offsets_xy[0] + size_xy[0])] = color
        except Exception as e:
            print(e)
            pass

    def update_record(self, frame_preview) -> None:
        cv2.imshow("Recording", frame_preview)
        if cv2.waitKey(1) == ord('q'):
            config.engine.release()

    def skip_track(self):
        self.update = self.real_update

    def pupil(self, source_rgb):
        if 'FullFOV' in config.engine.subject_parameters["Name"]:
            self.place_square(source_rgb,   [config.engine.subject_parameters["OffsetX"],config.engine.subject_parameters["OffsetY"]],
                                                    [config.engine.subject_parameters["Width"],config.engine.subject_parameters["Height"]], red)
            self.place_cross(source_rgb, [config.engine.subject_parameters["OffsetX"],config.engine.subject_parameters["OffsetY"]], blue)

        try:
            pupil_center, pupil_width, pupil_height, pupil_angle = self.pupil_processor.fit_model.params
            
            if pupil_width < config.engine.subject_parameters["min_radius"] or pupil_width > config.engine.subject_parameters["max_radius"]:
                cv2.ellipse(source_rgb, tuple_int(pupil_center), tuple_int((pupil_width, pupil_height)), pupil_angle, 0, 360, red, 1)
            else: 
                cv2.ellipse(source_rgb, tuple_int(pupil_center), tuple_int((pupil_width, pupil_height)), pupil_angle, 0, 360, green, 1)
            cv2.ellipse(source_rgb, tuple_int(pupil_center), tuple_int((config.engine.subject_parameters["min_radius"], config.engine.subject_parameters["min_radius"])), pupil_angle, 0, 360, blue, 1)
            cv2.ellipse(source_rgb, tuple_int(pupil_center), tuple_int((config.engine.subject_parameters["max_radius"], config.engine.subject_parameters["max_radius"])), pupil_angle, 0, 360, blue, 2)
            self.place_cross(source_rgb, pupil_center, red)

            return True
        except Exception as e:
            logger.info(f"pupil not found: {e}")
            return False

    def adj_update(self, img):
        source_rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        self.bin_P = self.bin_stock.copy()

        if self.pupil_(source_rgb):
            self.bin_P[0:20, 0:self.binary_width] = self.bin_stock_txt_selected
        else:
            self.bin_P[0:20, 0:self.binary_width] = self.bin_stock_txt

        try:
            pupil_area = self.pupil_processor.source
            offset_y = int((self.binary_height - pupil_area.shape[0]) / 2)
            offset_x = int((self.binary_width - pupil_area.shape[1]) / 2)
            self.bin_P[offset_y:min(offset_y + pupil_area.shape[0], self.binary_height),
            offset_x:min(offset_x + pupil_area.shape[1], self.binary_width)] = pupil_area
        except:
            pass

        self.bin_stock_txt = np.zeros((20, self.binary_width))
        cv2.putText(self.bin_stock_txt, 'Pupil | thresh R/F {} | blur T/G {}'.format(config.engine.subject_parameters["p_binarythreshold"],config.engine.subject_parameters["p_blur"]), (10, 15), font, .7, 1, 0, cv2.LINE_4)
        self.bin_P[0:20, 0:self.binary_width] = self.bin_stock_txt

        #self.cr1_(source_rgb)
        #self.cr2_(source_rgb)

        self.bin_CR = self.bin_stock.copy()

        try:
            cr_area = self.current_cr_processor.source
            offset_y = int((self.binary_height - cr_area.shape[0]) / 2)
            offset_x = int((self.binary_width - cr_area.shape[1]) / 2)
            self.bin_CR[offset_y:min(offset_y + cr_area.shape[0], self.binary_height),
            offset_x:min(offset_x + cr_area.shape[1], self.binary_width)] = cr_area
        except:
            pass

        self.crstock_txt = np.zeros((20, self.binary_width))
        cv2.putText(self.crstock_txt, 'CR | thresh W/S {} | blur E/D {}'.format(self.current_cr_processor.binarythreshold,self.current_cr_processor.blur[0]), (10, 15), font, .7, 1, 0, cv2.LINE_4)
        self.bin_CR[0:20, 0:self.binary_width] = self.crstock_txt

        cv2.imshow("BINARY", np.vstack((self.bin_P, self.bin_CR)))
        cv2.imshow("CONFIGURATION", source_rgb)

        # Update the GUI with data, if available
        if hasattr(config.engine,'pupil_x_volts'):
            self.plot.x.append(config.engine.pupil_x_volts)
            self.plot.y.append(config.engine.pupil_y_volts)
            self.plot.x = self.plot.x[-40:]
            self.plot.y = self.plot.y[-40:]
            self.plot.fig.canvas.restore_region(self.plot.bg)
            self.plot.ln.set_data(self.plot.x,self.plot.y)
            self.plot.ax2.draw_artist(self.plot.ln)
            self.plot.fig.canvas.blit(self.plot.fig.bbox)
            self.plot.fig.canvas.flush_events()

        self.key_listener(cv2.waitKey(25))
        if self.first_run:
            self.first_run = False


    def real_update(self, img) -> None:
        source_rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        self.pupil_(source_rgb)

        cv2.imshow("TRACKING", source_rgb)

        threading.Timer(self.fps, self.skip_track).start() #run feed every n secs (n=1)
        self.update = lambda _: None

        if cv2.waitKey(1) == ord("q"):
            config.engine.release()


# import os
# from pathlib import Path

# import numpy as np

# import eyeloop.config as config
# from eyeloop.constants.minimum_gui_constants import *
# from eyeloop.utilities.general_operations import to_int, tuple_int
# import threading

# import logging
# logger = logging.getLogger(__name__)

# class GUI:
#     def __init__(self) -> None:


#         dir_path = os.path.dirname(os.path.realpath(__file__))
#         tool_tip_dict = ["tip_1_cr", "tip_2_cr", "tip_3_pupil", "tip_4_pupil", "tip_5_start", "tip_1_cr_error", "",
#                          "tip_3_pupil_error"]
#         self.first_tool_tip = cv2.imread("{}/graphics/{}.png".format(dir_path, "tip_1_cr_first"), 0)
#         self.tool_tips = [cv2.imread("{}/graphics/{}.png".format(dir_path, tip), 0) for tip in tool_tip_dict]

#         self._state = "adjustment"
#         self.inquiry = "none"
#         self.terminate = -1
#         self.update = self.adj_update#real_update
#         self.skip = 0
#         self.first_run = True

#         self.pupil_ = lambda _: False
#         self.cr1_ = lambda _: False
#         self.cr2_ = lambda _: False





#     def tip_mousecallback(self, event, x: int, y: int, flags, params) -> None:
#         if event == cv2.EVENT_LBUTTONDOWN:
#             if 10 < y < 35:
#                 if 20 < x < 209:
#                     x -= 27
#                     x = int(x / 36) + 1

#                     self.update_tool_tip(x)

#     def mousecallback(self, event, x, y, flags, params) -> None:
#         x = x % self.width
#         self.cursor = (x, y)

#     def release(self):
#         #self.out.release()
#         cv2.destroyAllWindows()

#     def remove_mousecallback(self) -> None:
#         cv2.setMouseCallback("CONFIGURATION", lambda *args: None)
#         cv2.setMouseCallback("Tool tip", lambda *args: None)

#     def update_tool_tip(self, index: int, error: bool = False) -> None:
#         if error:
#             cv2.imshow("Tool tip", self.tool_tips[index + 4])
#         else:
#             cv2.imshow("Tool tip", self.tool_tips[index - 1])

#     def key_listener(self, key: int) -> None:
#         try:
#             key = chr(key)
#         except:
#             return

#         if self.inquiry == "track":
#             if "y" == key:
#                 print("Initiating tracking..")
#                 self.remove_mousecallback()
#                 cv2.destroyWindow("CONFIGURATION")
#                 cv2.destroyWindow("BINARY")
#                 cv2.destroyWindow("Tool tip")

#                 cv2.imshow("TRACKING", self.bin_stock)
#                 cv2.moveWindow("TRACKING", 100, 100)

#                 self._state = "tracking"
#                 self.inquiry = "none"

#                 self.update = self.real_update

#                 config.engine.activate()

#                 return
#             elif "n" == key:
#                 print("Adjustments resumed.")
#                 self._state = "adjustment"
#                 self.inquiry = "none"
#                 return

#         if self._state == "adjustment":
#             if key == "p":
#                 config.engine.angle -= 3

#             elif key == "o":
#                 config.engine.angle += 3

#             elif "1" == key:
#                 try:
#                     #config.engine.pupil = self.cursor
#                     self.pupil_processor.reset(self.cursor)
#                     self.pupil_ = self.pupil

#                     self.update_tool_tip(4)

#                     print("Pupil selected.\nAdjust binarization via R/F (threshold) and T/G (smoothing).")
#                 except Exception as e:
#                     self.update_tool_tip(3, True)
#                     logger.info(f"pupil selection failed; {e}")

#             elif "2" == key:
#                 try:

#                     self.cr_processor_1.reset(self.cursor)
#                     self.cr1_ = self.cr_1

#                     self.current_cr_processor = self.cr_processor_1

#                     self.update_tool_tip(2)

#                     print("Corneal reflex selected.\nAdjust binarization via W/S (threshold) and E/D (smoothing).")

#                 except Exception as e:
#                     self.update_tool_tip(1, True)
#                     logger.info(f"CR selection failed; {e}")

#             elif "3" == key:
#                 try:
#                     self.update_tool_tip(2)
#                     self.cr_processor_2.reset(self.cursor)
#                     self.cr2_ = self.cr_2

#                     self.current_cr_processor = self.cr_processor_2

#                     print("\nCorneal reflex selected.")
#                     print("Adjust binarization via W/S (threshold) and E/D (smoothing).")

#                 except:
#                     self.update_tool_tip(1, True)
#                     print("Hover and click on the corneal reflex, then press 3.")


#             elif "z" == key:
#                 print("Start tracking? (y/n)")
#                 self.inquiry = "track"

#             elif "w" == key:

#                 self.current_cr_processor.binarythreshold += 1

#                 # print("Corneal reflex binarization threshold increased (%s)." % self.CRProcessor.binarythreshold)

#             elif "s" == key:

#                 self.current_cr_processor.binarythreshold -= 1
#                 # print("Corneal reflex binarization threshold decreased (%s)." % self.CRProcessor.binarythreshold)

#             elif "e" == key:

#                 self.current_cr_processor.blur = tuple([x + 2 for x in self.current_cr_processor.blur])
#                 # print("Corneal reflex blurring increased (%s)." % self.CRProcessor.blur)

#             elif "d" == key:

#                 if self.current_cr_processor.blur[0] > 1:
#                     self.current_cr_processor.blur -= tuple([x - 2 for x in self.current_cr_processor.blur])
#                 # print("Corneal reflex blurring decreased (%s)." % self.CRProcessor.blur)

#             elif "r" == key:

#                 self.pupil_processor.binarythreshold += 1
#                 # print("Pupil binarization threshold increased (%s)." % self.pupil_processor.binarythreshold)
#             elif "f" == key:

#                 self.pupil_processor.binarythreshold -= 1
#                 # print("Pupil binarization threshold decreased (%s)." % self.pupil_processor.binarythreshold)

#             elif "t" == key:

#                 self.pupil_processor.blur = tuple([x + 2 for x in self.pupil_processor.blur])

#                 # print("Pupil blurring increased (%s)." % self.pupil_processor.blur)

#             elif "g" == key:
#                 if self.pupil_processor.blur[0] > 1:
#                     self.pupil_processor.blur = tuple([x - 2 for x in self.pupil_processor.blur])
#                 # print("Pupil blurring decreased (%s)." % self.pupil_processor.blur)

#         if "q" == key:
#             # Terminate tracking
#             config.engine.release()

#     def arm(self, width: int, height: int) -> None:
#         self.fps = np.round(1/config.arguments.fps, 2)

#         self.pupil_processor = config.engine.pupil_processor

#         self.cr_index = 0
#         self.current_cr_processor = config.engine.cr_processor_1  # primary corneal reflection
#         self.cr_processor_1 = config.engine.cr_processor_1
#         self.cr_processor_2 = config.engine.cr_processor_2

#         self.width, self.height = width, height
#         self.binary_width = max(width, 300)
#         self.binary_height = max(height, 200)

#         fourcc = cv2.VideoWriter_fourcc(*'MPEG')
#         output_vid = Path(config.file_manager.new_folderpath, "output.avi")
#         self.out = cv2.VideoWriter(str(output_vid), fourcc, 50.0, (self.width, self.height))

#         self.bin_stock = np.zeros((self.binary_height, self.binary_width))
#         self.bin_P = self.bin_stock.copy()
#         self.bin_CR = self.bin_stock.copy()
#         #self.CRStock = self.bin_stock.copy()

#         self.src_txt = np.zeros((20, width, 3))
#         self.prev_txt = self.src_txt.copy()
#         cv2.putText(self.src_txt, 'Source', (15, 12), font, .7, (255, 255, 255), 0, cv2.LINE_4)
#         cv2.putText(self.prev_txt, 'Preview', (15, 12), font, .7, (255, 255, 255), 0, cv2.LINE_4)
#         cv2.putText(self.prev_txt, 'EyeLoop', (width - 50, 12), font, .5, (255, 255, 255), 0, cv2.LINE_8)

#         self.bin_stock_txt = np.zeros((20, self.binary_width))
#         self.bin_stock_txt_selected = self.bin_stock_txt.copy()
#         self.crstock_txt = self.bin_stock_txt.copy()
#         self.crstock_txt[0:1, 0:self.binary_width] = 1
#         self.crstock_txt_selected = self.crstock_txt.copy()

#         cv2.putText(self.bin_stock_txt, 'P | R/F | T/G || bin/blur', (10, 15), font, .7, 1, 0, cv2.LINE_4)
#         cv2.putText(self.bin_stock_txt_selected, '(*) P | R/F | T/G || bin/blur', (10, 15), font, .7, 1, 0, cv2.LINE_4)

#         cv2.putText(self.crstock_txt, 'CR | W/S | E/D || bin/blur', (10, 15), font, .7, 1, 0, cv2.LINE_4)
#         cv2.putText(self.crstock_txt_selected, '(*) CR | W/S | E/D || bin/blur', (10, 15), font, .7, 1, 0, cv2.LINE_4)

#         cv2.imshow("CONFIGURATION", np.hstack((self.bin_stock, self.bin_stock)))
#         cv2.imshow("BINARY", np.vstack((self.bin_stock, self.bin_stock)))

#         cv2.moveWindow("BINARY", 105 + width * 2, 100)
#         cv2.moveWindow("CONFIGURATION", 100, 100)

#         cv2.imshow("Tool tip", self.first_tool_tip)

#         cv2.moveWindow("Tool tip", 100, 1000 + height + 100)
#         try:
#             cv2.setMouseCallback("CONFIGURATION", self.mousecallback)
#             cv2.setMouseCallback("Tool tip", self.tip_mousecallback)
#         except:
#             print("Could not bind mouse-buttons.")

#     def place_cross(self, source: np.ndarray, point: tuple, color: tuple) -> None:
#         try:
#             source[to_int(point[1] - 3):to_int(point[1] + 4), to_int(point[0])] = color
#             source[to_int(point[1]), to_int(point[0] - 3):to_int(point[0] + 4)] = color
#         except:
#             pass


#     def update_record(self, frame_preview) -> None:
#         cv2.imshow("Recording", frame_preview)
#         if cv2.waitKey(1) == ord('q'):
#             config.engine.release()

#     def skip_track(self):
#         self.update = self.real_update


#     def pupil(self, source_rgb):
#         try:
#             pupil_center, pupil_width, pupil_height, pupil_angle = self.pupil_processor.fit_model.params

#             cv2.ellipse(source_rgb, tuple_int(pupil_center), tuple_int((pupil_width, pupil_height)), pupil_angle, 0, 360, red, 1)
#             self.place_cross(source_rgb, pupil_center, red)
#             return True
#         except Exception as e:
#             logger.info(f"pupil not found: {e}")
#             return False

#     def cr_1(self, source_rgb):
#         try:
#             #cr_center, cr_width, cr_height, cr_angle = params = self.cr_processor_1.fit_model.params

#             #cv2.ellipse(source_rgb, tuple_int(cr_center), tuple_int((cr_width, cr_height)), cr_angle, 0, 360, green, 1)
#             self.place_cross(source_rgb, self.cr_processor_1.center, green)
#             return True
#         except Exception as e:
#             logger.info(f"cr1 func: {e}")
#             return False

#     def cr_2(self, source_rgb):
#         try:
#             #cr_center, cr_width, cr_height, cr_angle = params = self.cr_processor_2.fit_model.params

#             #cv2.ellipse(source_rgb, tuple_int(cr_center), tuple_int((cr_width, cr_height)), cr_angle, 0, 360, green, 1)
#             self.place_cross(source_rgb, self.cr_processor_2.center, green)
#             return True
#         except Exception as e:
#             logger.info(f"cr2 func: {e}")
#             return False

#     def adj_update(self, img):
#         source_rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

#         #if self.pupil_(source_rgb):
#         self.bin_P = self.bin_stock.copy()

#         if self.pupil_(source_rgb):
#             self.bin_P[0:20, 0:self.binary_width] = self.bin_stock_txt_selected
#         else:
#             self.bin_P[0:20, 0:self.binary_width] = self.bin_stock_txt

#         #self.bin_CR = self.bin_stock.copy()

#         try:
#             pupil_area = self.pupil_processor.source

#             offset_y = int((self.binary_height - pupil_area.shape[0]) / 2)
#             offset_x = int((self.binary_width - pupil_area.shape[1]) / 2)
#             self.bin_P[offset_y:min(offset_y + pupil_area.shape[0], self.binary_height),
#             offset_x:min(offset_x + pupil_area.shape[1], self.binary_width)] = pupil_area
#         except:
#             pass

#         self.cr1_(source_rgb)
#         self.cr2_(source_rgb)

#         self.bin_CR = self.bin_stock.copy()

#         try:
#             cr_area = self.current_cr_processor.source
#             offset_y = int((self.binary_height - cr_area.shape[0]) / 2)
#             offset_x = int((self.binary_width - cr_area.shape[1]) / 2)
#             self.bin_CR[offset_y:min(offset_y + cr_area.shape[0], self.binary_height),
#             offset_x:min(offset_x + cr_area.shape[1], self.binary_width)] = cr_area
#             self.bin_CR[0:20, 0:self.binary_width] = self.crstock_txt_selected
#         except:
#             self.bin_CR[0:20, 0:self.binary_width] = self.crstock_txt
#             pass




#         #print(cr_area)

#         cv2.imshow("BINARY", np.vstack((self.bin_P, self.bin_CR)))
#         cv2.imshow("CONFIGURATION", source_rgb)
#         #self.out.write(source_rgb)

#         self.key_listener(cv2.waitKey(50))
#         if self.first_run:
#             cv2.destroyAllWindows()
#             self.first_run = False


#     def real_update(self, img) -> None:
#         source_rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
#         self.pupil_(source_rgb)
#         self.cr1_(source_rgb)
#         self.cr2_(source_rgb)

#         cv2.imshow("TRACKING", source_rgb)

#         threading.Timer(self.fps, self.skip_track).start() #run feed every n secs (n=1)
#         self.update = lambda _: None

#         if cv2.waitKey(1) == ord("q"):


#             config.engine.release()
