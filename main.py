from cascade_detection import Detection
from controller import Controller
import cv2
from motor import CalibratedMotor, Motor
import pigpio
import time
from LineTracking import LineTracking
from print_distance import Sonic

drive_motor = Motor(Motor._bp.PORT_B)
steer_motor = CalibratedMotor(Motor._bp.PORT_D, calpow=30)

def drive_steer(pos_new):
    pos = steer_motor.position_from_factor(pos_new)
    steer_motor.change_position(pos)

def drive_power(power_new):
    drive_motor.change_power(power_new)

def stop_all():
    drive_motor.stop()
    steer_motor.stop()

def main():
    ###Kameraaufnahme starten
    cap = cv2.VideoCapture(0)
    ###Detectionobjekt für Palettenerkennung
    det = Detection()
    ###Linetracking und controller-Objekt für Linetracking
    lt = LineTracking()
    controller = Controller()

    sonic = Sonic()

    steer_motor.calibrate()

    state = 0
    pi = pigpio.pi()

    if not pi.connected:
        exit(0)
    try:
        while True:
            ret, image = cap.read()
            distances = sonic.getDistance(2)
            
            dist_front_l = distances[1]
            dist_front_r = distances[0]
            width = 640
            height = 480

            if(state == 0):
                print("Following line! Distance front left/front right: {}/{}".format(dist_front_r, dist_front_l))
                if(dist_front_l > 40 or dist_front_r > 40):
                    ###Linie folgen
                    drive_steer(0)
                    drive_power(-30)
                    val = lt.track_line(image, False)
                    pid = controller.pid(val)
                    drive_steer(pid/100)
                else:
                    drive_power(0)
                    state = 1
            elif(state == 1):
                print("Object in front!")
                det = Detection()
                ###Aktuelles Bild an det übergeben -> Palette erkennen
                (x, y, w, h), image = det.detect_palette(image)
                ###Wenn detect_palette(image) -1 zurückgibt, wurde keine Palette erkannt
                if(x == -1):
                    ###Wenn keine Palette erkannt wurde -> x-Wert so setzen, dass er rechts vorbei fährt
                    x = 1000
                if(x < int(width / 2)):
                    print("Pallet more on the right side -> drive around the left")
                    state = 2
                else:
                    print("Pallet more on the left side -> drive around the right")
                    state = 3
            elif(state == 2):
                ###Solange nach vorne links fahren, bis rechter Sensor über die Palette hinaus ist, dann noch etwas weiter fahren
                print("Entfernung vorne rechts: {}".format(dist_front_r))
                print("Drive around left!")
                if(dist_front_r > 80):
                    print("Right sensor past the pallet!")
                    drive_steer(-0.8)
                    drive_power(-30)
                    time.sleep(0.5)
                    drive_power(0)
                    state = 4
                else:
                    drive_steer(-0.8)
                    drive_power(-30)
            elif(state == 3):
                ###Solange nach vorne rechts fahren, bis linker Sensor über die Palette hinaus ist, dann noch etwas weiter fahren
                print("Drive around right!")
                if(dist_front_l > 80):
                    print("Left sensor past the pallet!")
                    drive_steer(0.8)
                    drive_power(-30)
                    time.sleep(0.5)
                    drive_power(0)
                    state = 5
                else:
                    drive_steer(0.8)
                    drive_power(-30)
            elif(state == 4):
                ###track_line(image) gibt solange -1 zurück, bis eine Linie erkannt wurde
                print("Trying to return on line!")
                val = lt.track_line(image, True)
                print(val)
                if(val == -1):
                    drive_steer(1)
                    drive_power(-30)
                else:
                    drive_steer(-0.8)
                    time.sleep(1.2)
                    drive_power(0)
                    state = 0
            elif(state == 5):
                print("Trying to return on line!")
                val = lt.track_line(image, True)
                print(val)
                if(val == -1):
                    drive_steer(-1)
                    drive_power(-30)
                else:
                    drive_steer(0.8)
                    time.sleep(1.2)
                    drive_power(0)
                    state = 0
            ###Aktuelles  Bild anzeigen
            cv2.imshow("frame", image)
            cv2.waitKey(1)
    except KeyboardInterrupt:
        print("\nCTRL-C pressed. Cleaning up and exiting!")
    finally:
        ###Alles sicher beenden
        cap.release()
        cv2.destroyAllWindows()
        pi.stop()
        stop_all()

main()