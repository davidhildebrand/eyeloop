import time
import threading
import eyeloop.config as config

class FPS_extractor:
    """
    Simple fps-counter. Acts as an interface. Pass it to CORE(interfaces=[..]) in puptrack.py.
    """

    def __init__(self):
        self.fetch = lambda _: None
        self.activate = lambda: None

        self.last_frame = 0

        self.thread = threading.Timer(1, self.get_fps)
        self.thread.start()


    def get_fps(self):
        print(f"    Processing {config.importer.frame - self.last_frame} frames per second.")
        try: # FPS_extractor is initialized before the importer... so the line below will not worked until the importer is loaded
            if config.importer.experiment_started and config.engine.save_images:
                print(f"    Microscope frame counter: {config.importer.frame_counter_scope}.")
        except:
            print("Please choose a config option from the GUI")
        self.last_frame = config.importer.frame
        self.thread = threading.Timer(1, self.get_fps)
        self.thread.start()


    def release(self, core):
        self.thread.cancel()
