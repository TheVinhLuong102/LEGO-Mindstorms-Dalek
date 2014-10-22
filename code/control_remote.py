#!/usr/bin/env python
"""Use this script to control the Dalek remotely. This is the script
you run on the controlling machine; run remote_receiver.py on the
Dalek itself."""


import argparse
from dalek_common import EventQueue, RunAfterTime, RepeatingAction, DurationAction
from dalek_network import Controller, DRIVE, TURN, HEAD_TURN
import io
import PIL.Image
import pygame
import random
import subprocess
import sys
import time



class RemoteController(Controller):
    def __init__(self, addr, snapshot_file):
        super(RemoteController, self).__init__(addr)
        self.snapshot_file = snapshot_file

    def snapshot_received(self, data):
        PIL.Image.open(io.BytesIO(data)).rotate(90).save(self.snapshot_file, "JPEG")
        with open("/dev/null", "w") as f:
            subprocess.call(["xdg-open", self.snapshot_file], stdout=f, stderr=f)


class Main(object):

    FRAME_RATE = 60
    TICK_LENGTH_SECONDS = 1.0 / float(FRAME_RATE)
    REPEAT_TIME_SECONDS = 5

    sound_dict = {pygame.K_1: "exterminate",
                  pygame.K_2: "gun",
                  pygame.K_3: "exterminate-exterminate-exterminate",
                  pygame.K_4: "identify-yourself",
                  pygame.K_5: "report",
                  pygame.K_6: "social-interaction-will-cease",
                  pygame.K_7: "why",
                  pygame.K_8: "you-would-make-a-good-dalek",
                  pygame.K_9: "doctor",
                  pygame.K_0: "the-doctor",
                  pygame.K_F1: "would-you-care-for-some-tea",
                  pygame.K_F2: "can-i-be-of-assistance",
                  pygame.K_F3: "please-excuse-me",
                  pygame.K_F4: "explain",
                  pygame.K_F5: "cease-talking",
                  pygame.K_F6: "that-is-incorrect",
                  pygame.K_F7: "you-will-follow",
                  pygame.K_F8: "daleks-are-supreme",
                  pygame.K_F9: "you-will-be-necessary",
                  pygame.K_F10: "you-will-identify",
                  pygame.K_F11: "it-is-the-doctor",
                  pygame.K_F12: "the-doctor-must-die",
                  pygame.K_p: "bring-him-to-me",
                  pygame.K_i: "i-bring-you-the-human",
                  pygame.K_u: "your-loyalty-will-be-rewarded",
                  pygame.K_y: "daleks-do-not-question-orders",
                  pygame.K_t: "which-of-you-is-least-important",
                  pygame.K_l: "this-human-is-our-best-option",
                  pygame.K_k: "i-have-duties-to-perform",
                  pygame.K_j: "daleks-have-no-concept-of-worry",
                  pygame.K_o: "then-hear-me-talk-now"}

    def __init__(self, addr, snapshot_file):
        super(Main, self).__init__()
        self.screen = pygame.display.set_mode((320, 240))
        self.font = pygame.font.Font(None, 40)
        self.screen_text = ""
        self.controller = RemoteController(addr, snapshot_file)
        self.drive_queue = EventQueue()
        self.other_queue = EventQueue()

        self.random_mode = False

        try:
            self.main_loop()
        finally:
            self.controller.exit()

    def begin_cmd_action(self, cmd, value, repeat):
        def action():
            self.controller.begin_cmd(cmd, value)

        if repeat:
            return RepeatingAction(Main.REPEAT_TIME_SECONDS, action, Main.TICK_LENGTH_SECONDS)
        else:
            return action

    def release_cmd_action(self, cmd, value):
        def action():
            self.controller.release_cmd(cmd, value)
        return action

    def timed_key_press_action(self, seconds, cmd, value):
        return DurationAction(seconds,
                              self.begin_cmd_action(cmd, value, False),
                              self.release_cmd_action(cmd, value),
                              Main.TICK_LENGTH_SECONDS)

    def stop_action(self):
        def action():
            self.controller.stop()
        return action

    def start_random_mode(self):
        if not self.random_mode:
            self.random_mode = True
            self.controller.stop()
            self.drive_queue.clear()
            self.other_queue.clear()
            self.drive_queue.add(RandomModeAction(self))

    def maybe_stop_random_mode(self, manual):
        if self.random_mode and manual:
            self.random_mode = False
            self.controller.stop()
            self.drive_queue.clear()
            self.other_queue.clear()


    def begin_drive_cmd(self, cmd, value, repeat, manual=True):
        self.maybe_stop_random_mode(manual)
        self.drive_queue.replace(self.begin_cmd_action(cmd, value, repeat))

    def release_drive_cmd(self, cmd, value, manual=True):
        self.maybe_stop_random_mode(manual)
        self.drive_queue.replace(self.release_cmd_action(cmd, value))

    def begin_head_cmd(self, cmd, value, manual=True):
        self.maybe_stop_random_mode(manual)
        self.other_queue.add(self.begin_cmd_action(cmd, value, False))

    def release_head_cmd(self, cmd, value, manual=True):
        self.maybe_stop_random_mode(manual)
        self.other_queue.add(self.release_cmd_action(cmd, value))

    def main_loop(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                elif event.type == pygame.KEYDOWN:
                    self.screen_text = "down: " + pygame.key.name(event.key)
                    if event.key == pygame.K_ESCAPE:
                        return
                    elif event.key == pygame.K_w:
                        self.begin_drive_cmd(DRIVE, 1.0, True)
                    elif event.key == pygame.K_s:
                        self.begin_drive_cmd(DRIVE, -1.0, True)
                    elif event.key == pygame.K_a:
                        self.begin_drive_cmd(TURN, -1.0, True)
                    elif event.key == pygame.K_d:
                        self.begin_drive_cmd(TURN, 1.0, True)
                    elif event.key == pygame.K_q:
                        self.begin_head_cmd(HEAD_TURN, -1.0)
                    elif event.key == pygame.K_e:
                        self.begin_head_cmd(HEAD_TURN, 1.0)
                    elif event.key == pygame.K_RETURN:
                        self.controller.snapshot()
                    elif event.key == pygame.K_v:
                        self.controller.toggle_verbose()
                    elif event.key == pygame.K_SPACE:
                        self.start_random_mode()
                    elif event.key in Main.sound_dict:
                        self.controller.play_sound(Main.sound_dict[event.key])
                elif event.type == pygame.KEYUP:
                    self.screen_text = "up: " + pygame.key.name(event.key)
                    if event.key == pygame.K_w:
                        self.release_drive_cmd(DRIVE, 1.0)
                    elif event.key == pygame.K_s:
                        self.release_drive_cmd(DRIVE, -1.0)
                    elif event.key == pygame.K_a:
                        self.release_drive_cmd(TURN, -1.0)
                    elif event.key == pygame.K_d:
                        self.release_drive_cmd(TURN, 1.0)
                    elif event.key == pygame.K_q:
                        self.release_head_cmd(HEAD_TURN, -1.0)
                    elif event.key == pygame.K_e:
                        self.release_head_cmd(HEAD_TURN, 1.0)

            self.drive_queue.process()
            self.other_queue.process()

            self.screen.fill((255, 255, 255))
            disp = self.font.render(self.screen_text, True, (0, 0, 0))
            rect = disp.get_rect()
            rect.left = 100
            rect.top = 100
            self.screen.blit(disp, rect)
            pygame.display.flip()
            time.sleep(1/float(Main.FRAME_RATE))


class RandomModeAction(object):

    TIMER_MIN = 10 * Main.FRAME_RATE
    TIMER_MAX = 30 * Main.FRAME_RATE

    def __init__(self, parent):
        super(RandomModeAction, self).__init__()
        self.parent = parent
        self.timer = random.randint(RandomModeAction.TIMER_MIN, RandomModeAction.TIMER_MAX)

    def random_drive_action(self, cmd):
        self.parent.drive_queue.add(self.parent.timed_key_press_action(random.uniform(1, 8),
                                                                       cmd,
                                                                       random.uniform(-0.5, 0.5)))

    def random_head_action(self):
        self.parent.other_queue.add(self.parent.timed_key_press_action(random.uniform(1, 3),
                                                                       HEAD_TURN,
                                                                       random.uniform(-0.5, 0.5)))

    def random_speech(self):
        self.parent.controller.play_sound(random.choice(Main.sound_dict))

    def __call__(self):
        if self.timer <= 0:
            choice = random.randint(0, 3)
            if choice == 0:
                self.random_drive_action(DRIVE)
            elif choice == 1:
                self.random_drive_action(TURN)
            elif choice == 2:
                self.random_head_action()
            elif choice == 3:
                self.random_speech()
        else:
            self.timer -= 1
        return True


pygame.init()

parser = argparse.ArgumentParser(description="Control the Dalek remotely from another machine")
parser.add_argument("addr", help="Address of the Dalek")
parser.add_argument("snapshotFile", help="File in which to save snapshots")

args = parser.parse_args()

Main(args.addr, args.snapshotFile)
sys.exit(0)
