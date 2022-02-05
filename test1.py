from PyQt5.QtWidgets import QMainWindow, QApplication, QVBoxLayout, QWidget, QLabel, QHBoxLayout, QListWidgetItem, \
    QPushButton, QSizePolicy, QAction, QAbstractItemView, QListWidget, QListView, QFileDialog
from PyQt5.QtGui import QIcon, QPixmap, QCursor, QImage, QIntValidator
from PyQt5.QtCore import QSize, Qt, QThreadPool, QTimeLine
from moviepy.editor import VideoFileClip, concatenate_videoclips
import datetime
import threading
from guia2 import Ui_MainWindow
import sys
import os
import cv2
import numpy as np
import multiprocessing
from proglog import ProgressBarLogger
from process import ProcessVideo, ExtractClips
print(multiprocessing.cpu_count())

# pyuic5 b2.ui -o guia2.py
# pyuic5 b3.ui -o guia2.py
ui_path = os.path.dirname(os.path.abspath(__file__))


class MyBarLogger(ProgressBarLogger):

    def callback(self, **changes):
        #         print('called', changes)
        # Every time the logger is updated, this function is called with
        # the `changes` dictionnary of the form `parameter: new value`.
        #         for p in changes.items():
        #             print(p)
        # for (parameter, new_value) in changes.items():
            # if parameter == 'progress':
            #     self.update(new_value)
        def bars_callback(self, bar, attr, value, old_value=None):
            # Every time the logger progress is updated, this function is called
            percentage = (value / self.bars[bar]['total']) * 100
            print(bar, attr, percentage)
            #             print ('Parameter %s is now %s' % (parameter, new_value))

    def update(self, prog):
        print(prog)
class OCR(QMainWindow):


    def __init__(self):
        super(OCR, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.resource_path = ui_path + '\\resources\\'
        self.times = None
        self.video = None
        self.all_sub = False
        self.divided = False
        self.logger = MyBarLogger()
        self.ui.btn_load_movie.clicked.connect(self.load_video)
        self.ui.btn_load_subtitle.clicked.connect(self.load_subtitle)
        self.ui.btn_change_location.clicked.connect(self.change_location)
        self.save_location = ui_path
        self.ui.label_save_location.setText(ui_path)
        self.onlyInt = QIntValidator()
        self.ui.line_start.setValidator(self.onlyInt)
        self.ui.line_end.setValidator(self.onlyInt)
        self.ui.line_gap.setValidator(self.onlyInt)
        self.ui.line_forward.setValidator(self.onlyInt)
        self.ui.line_backward.setValidator(self.onlyInt)
        self.ui.line_words_each.setValidator(self.onlyInt)
        self.ui.line_lines_each.setValidator(self.onlyInt)

        self.thread_counts = multiprocessing.cpu_count()

        self.ui.label_cores.setText(str(self.thread_counts))
        self.ui.spin_cores.setMaximum(self.thread_counts)
        self.ui.spin_cores.setMinimum(1)
        self.ui.spin_cores.setValue(1)

        self.ui.btn_run.clicked.connect(self.run)

        self.threadpool = QThreadPool()
        self.worker_process = None

        self.active = True

    def change_location(self):
        options = QFileDialog.Options()
        save_location= QFileDialog.getExistingDirectory(self, 'Video File and SRT File Save Location',
                                                        self.save_location,
                                                        options=options)
        print(save_location)
        if save_location == '':
            return
        self.save_location = save_location
        self.ui.label_save_location.setText(self.save_location)
    def process_finished(self,):
        self.active = True
        print('finished')
    def deliver_video(self, video_clips):
            try:
                cores = self.ui.spin_cores.value()
                print(cores, 'cores')
                codec = self.ui.combo_codec.currentText()
                print('codec', codec)
                extension = self.ui.combo_extension.currentText()
                print('exte', extension)
                if (codec == 'libx265' and extension == 'WMV') or (codec == 'libx265' and extension == 'AVI'):
                    print('not support other extension or use libx264')
                    return
                if codec == 'rawvideo' and extension != 'AVI':
                    print('use AVI for rawvidow only')
                    return
                audio = self.ui.check_audio.isChecked()
                print('audi', audio)


                if self.ui.combo_fps.currentText() == 'Source FPS':
                    fps = None
                else:
                    fps = float(self.ui.combo_fps.currentText())
                print('fps', fps)
                preset = self.ui.combo_preset.currentText()
                audio_codec = self.ui.combo_codec_audio.currentText()
                print(audio_codec)
                if self.ui.combo_bitrate.currentText() == 'Source Bitrate':
                    print('yes')
                    bitrate = None
                else:
                    bitrate = self.ui.combo_bitrate.currentText()
                print(bitrate)
                self.worker = ProcessVideo(video_clips, codec, audio_codec, preset,
                                                  cores, fps, bitrate, audio, extension,
                                           self.save_location, self.file_name)

                self.worker.signals.finished.connect(self.process_finished)
                self.threadpool.start(self.worker)
                print('start')
            except Exception as e:
                print('error delive', repr(e))
                self.active = True



    def run(self):
        if self.active:
            try:
                if self.video is None:
                    print('no video')

                    return
                if self.times is None:
                    print('no sub')
                    return

                self.starting_subtitle = self.ui.line_start.text()
                if self.starting_subtitle != '' :
                    self.starting_subtitle = int(self.starting_subtitle)
                else:
                    print('starting')
                    return
                self.ending_subtitle = self.ui.line_end.text()
                if self.ending_subtitle != '':
                    self.ending_subtitle = int(self.ending_subtitle)
                else:
                    print('ending')
                    return

                if self.starting_subtitle == 0:
                    print('start from 1')
                    return
                if self.ending_subtitle > len(self.times):
                    print('ending exceed')
                    return
                if self.ending_subtitle < self.starting_subtitle :
                    print('ending lower')
                    return
                self.active = False

                if self.ui.line_gap.text() != '':
                    self.gap = int(self.ui.line_gap.text())
                else :
                    self.gap = 0
                    self.ui.line_gap.setText('0')

                if self.ui.line_forward.text() != '':
                    self.forward = int(self.ui.line_forward.text())
                else :
                    self.forward = 0
                    self.ui.line_forward.setText('0')


                if self.ui.line_backward.text() != '':
                    self.backward = int(self.ui.line_backward.text())
                else :
                    self.backward = 0
                    self.ui.line_backward.setText('0')

                self.starting_subtitle -= 1
                # ending_subtitle -=  1
                s = None
                s_history = []
                n_times = []

                time_zero = datetime.datetime.strptime('00:00:00', '%H:%M:%S')
                words_each_file = self.ui.line_words_each.text()
                if words_each_file != '' :
                    words_each_file = int(words_each_file)

                self.target_width = self.ui.line_width.text()
                if self.target_width != '':
                    self.target_width = int(self.target_width)
                else :
                    print('target width')
                    self.active = True

                    return
                self.target_height = self.ui.line_height.text()
                if self.target_height != '':
                    self.target_height = int(self.target_height)
                else:
                    print(' target_height')
                    self.active = True
                    return

                if self.target_height != self.targett_height or self.target_width != self.targett_width:
                    self.video = VideoFileClip(self.file_name,
                                               target_resolution=(self.target_width, self.target_height))
                for i in range(self.starting_subtitle, self.ending_subtitle):

                    if i - self.starting_subtitle == 0:
                        if self.times[i][0] - datetime.timedelta(seconds=self.backward) > time_zero:
                            s = self.times[i][0] - datetime.timedelta(seconds=self.backward)
                        else:
                            s = self.times[i][0]
                    else:

                        if (self.times[i][0] - datetime.timedelta(seconds=self.backward) \
                            - self.times[i - 1][1] - datetime.timedelta(seconds=self.forward)) \
                                < datetime.timedelta(seconds=self.gap):

                            s += self.times[i][0] - self.times[i - 1][1] - (self.times[i][0] - self.times[i - 1][1])
                        else:
                            s += self.times[i][0] - self.times[i - 1][1] - datetime.timedelta(seconds=self.forward) - \
                                 datetime.timedelta(seconds=self.backward)

                    n_d1 = self.times[i][0] - s
                    n_d2 = self.times[i][1] - s
                    s_history.append(s)
                    if str(n_d1).split(':')[2] == '00' or '.' not in str(n_d1).split(':')[2]:
                        n_d1 = datetime.datetime.strptime(str(n_d1) + '.00', "%H:%M:%S.%f")
                    else:
                        n_d1 = datetime.datetime.strptime(str(n_d1), "%H:%M:%S.%f")
                    if str(n_d2).split(':')[2] == '00' or '.' not in str(n_d2).split(':')[2]:
                        n_d2 = datetime.datetime.strptime(str(n_d2) + '.00', "%H:%M:%S.%f")
                    else:
                        n_d2 = datetime.datetime.strptime(str(n_d2), "%H:%M:%S.%f")
                    n_times.append([n_d1, n_d2])
                #     print(n_d1))
                cut_list = []
                if self.divided:
                    k = 0
                    run = True
                    j = 1
                    while run:
                        srt_file_name = self.save_location + '/' + str(j) + '--' + \
                        self.file_name.split('/')[-1].split('.')[0] + '.srt'

                        with open(srt_file_name, 'w') as file:
                            #     for i in range(len(n_times)):
                            len_words = 0
                            start = k
                            first_line = 0
                            first_time = n_times[k][0]
                            for i in range(k, len(n_times)):

                                sub = ''
                                file.write(str(i + 1) + '\n')
                                first_line += 1
                                if j == 1:
                                    file.write(datetime.datetime.strftime(n_times[i][0], '%H:%M:%S,%f')[:-3] + ' --> ' +
                                               datetime.datetime.strftime(n_times[i][1], '%H:%M:%S,%f')[:-3] + '\n')
                                else:
                                    s = n_times[i][0] - first_time + datetime.timedelta(seconds=self.backward)
                                    e = n_times[i][1] - first_time + datetime.timedelta(seconds=self.backward)
                                    if str(n_d1).split(':')[2] == '00' or '.' not in str(s).split(':')[2]:
                                        s = datetime.datetime.strptime(str(s) + '.00', "%H:%M:%S.%f")
                                    else:
                                        s = datetime.datetime.strptime(str(s), "%H:%M:%S.%f")
                                    if str(e).split(':')[2] == '00' or '.' not in str(e).split(':')[2]:
                                        e = datetime.datetime.strptime(str(e) + '.00', "%H:%M:%S.%f")
                                    else:
                                        e = datetime.datetime.strptime(str(e), "%H:%M:%S.%f")
                                    file.write(datetime.datetime.strftime(s, '%H:%M:%S,%f')[:-3] + ' --> ' +
                                               datetime.datetime.strftime(e, '%H:%M:%S,%f')[:-3] + '\n')
                                for s in self.subs.split('\n\n')[i + self.starting_subtitle].split('\n')[2:]:
                                    sub += s + '\n'
                                len_words += len(sub.split())
                                file.write(sub)
                                file.write('\n')

                                #                 print(k, i)
                                if len_words > words_each_file or i == len(n_times) - 1:
                                    print('yes', len_words, i)
                                    j += 1
                                    k = i + 1
                                    cut_list.append((start, i))
                                    #                 file.close()
                                    break

                            #         print('nnn', k)
                            if k == len(n_times):
                                run = False
                else:
                    j = 1
                    srt_file_name = self.save_location + '/' + str(j) + '--' + \
                                    self.file_name.split('/')[-1].split('.')[0] + '.srt'
                    with open(srt_file_name, 'w') as file:

                        #     for i in range(len(n_times)):
                        for i in range(len(n_times)):
                            sub = ''
                            file.write(str(i + 1) + '\n')
                            file.write(datetime.datetime.strftime(n_times[i][0], '%H:%M:%S,%f')[:-3] + ' --> ' +
                                       datetime.datetime.strftime(n_times[i][1], '%H:%M:%S,%f')[:-3] + '\n')
                            for s in self.subs.split('\n\n')[i + self.starting_subtitle].split('\n')[2:]:
                                sub += s + '\n'
                            file.write(sub)
                            file.write('\n')
                        cut_list.append((0, - 1 + self.ending_subtitle - self.starting_subtitle))
                self.worker2 = ExtractClips(self.times, cut_list, self.video, self.forward, self.backward,
                                            self.gap, self.starting_subtitle, self.ending_subtitle)
                self.worker2.signals.finished.connect(self.extract_cliped_finished)
                self.worker2.run()
                # self.extract_clips(cut_list)

            except Exception as e:
                print('error', repr(e))
                self.active = True

        else:
            print('wait')
    def extract_cliped_finished(self, status, video_clips):
        if status == 'ok':
            print('finish3')
            self.deliver_video(video_clips)
        else:
            self.active = True
            print('error extract clip')
    def extract_clips(self, cut_list):
        try:
            video_clips = []
            for t in cut_list:
                start = self.starting_subtitle + t[0]
                end = self.starting_subtitle + t[1] + 1
                clips = []
                time_zero = datetime.datetime.strptime('00:00:00', '%H:%M:%S')
                history = None
                final_cuts = []

                for i in range(start, end):

                    d1 = self.times[i][0]
                    if d1 - datetime.timedelta(seconds=self.forward) > time_zero:
                        d1 = self.times[i][0] - datetime.timedelta(seconds=self.backward)

                    d2 = self.times[i][1] + datetime.timedelta(seconds=self.forward)

                    if i - start - 1 >= 0:

                        if (d1 - history) < datetime.timedelta(seconds=self.gap):
                            if i + 1 == end:
                                #                             print('yes', final_cuts[-1][1])
                                final_cuts[-1][1] = datetime.datetime.strftime(d2 + \
                                                           datetime.timedelta(seconds=self.forward),
                                                                               '%H:%M:%S,%f')[:-3]
                            #                             print('yes', final_cuts[-1][1] )
                            else:
                                final_cuts[-1][1] = datetime.datetime.strftime(d2, '%H:%M:%S,%f')[:-3]

                            history = d2
                            #                     print('cont')
                            continue

                    history = d2

                    startt = datetime.datetime.strftime(d1, '%H:%M:%S,%f')[:-3]

                    endd = datetime.datetime.strftime(d2, '%H:%M:%S,%f')[:-3]

                    final_cuts.append([startt, endd])
                for c in final_cuts:
                    clip = self.video.subclip(c[0], c[1])
                    clips.append(clip)

                final_clip = concatenate_videoclips(clips)
                video_clips.append(final_clip)

            self.deliver_video(video_clips)
        except Exception as e:
            print('error extract clip', repr(e))
            self.active = True

    def load_video(self):
        options = QFileDialog.Options()
        self.file_name, _ = QFileDialog.getOpenFileName(self, 'Open Video file', '',
                                                   "Videos (*.mp4 *.mkv *mov *avi *wmv)",
                                                   options=options)
        print(self.file_name)
        if self.file_name == '':
            return
        try:
            self.video = VideoFileClip(self.file_name)
            self.ui.label_video_name.setText(self.file_name.split('/')[-1])
            self.ui.label_video_duration.setText(
                str(datetime.timedelta(seconds=self.video.duration)).split('.')[0])
            self.targett_width = self.video.size[0]
            self.targett_height = self.video.size[1]
            self.ui.label_video_resolution.setText(str(self.video.size[0]) + ' * ' + str(self.video.size[1]))
            self.ui.label_video_fps.setText(str(round(self.video.fps, 2)))
            self.ui.line_width.setText(str(self.video.size[0]))
            self.ui.line_height.setText(str(self.video.size[1]))
        except Exception as e:
            print('load video fail')
            print(repr(e))
        # index = self.ui.combo_fps.findText(str(round(self.video.fps, 2)))
        # # index = self.ui.combo_fps.findText('2')
        # if index == -1 :
        #     new_fps = str(round(self.video.fps, 2))
        #     self.ui.combo_fps.addItem(new_fps)
        #     index = self.ui.combo_fps.findText(new_fps)
        # self.ui.combo_fps.setCurrentIndex(index)




    def load_subtitle(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, 'Open Subtitle file', '',
                                                   "Subtitle (*.srt)",
                                                   options=options)
        print(file_name)
        if file_name != '':
            try:
                lines = []

                with open(file_name, 'r') as file:
                    for line in file:
                        lines.append(line)
                self.times = []
                self.subs = ''
                for i, line in enumerate(lines):
                    self.subs += line
                    if ':' in line and '-->' in line:
                        time = line.split('-->')
                        try:
                            d1 = datetime.datetime.strptime(time[0].strip(), '%H:%M:%S,%f')
                        except Exception as e:
                            d1 = datetime.datetime.strptime(time[0].strip(), '%H:%M:%S')
                        try:
                            d2 = datetime.datetime.strptime(time[1].strip(), '%H:%M:%S,%f')
                        except Exception as e:
                            d2 = datetime.datetime.strptime(time[1].strip(), '%H:%M:%S')
                        self.times.append([d1, d2])
                self.ui.label_subtitle_name.setText(file_name.split('/')[-1])
                # print(str(len(times)))
                self.ui.label_subtitle_lines.setText(str(len(self.times)))
            except Exception as e:
                print('srt load error', repr(e))

if __name__ == '__main__':

    app = QApplication([])
    window = OCR()
    # window.make_center()
    # window.left_window()
    window.show()
    sys.exit(app.exec())