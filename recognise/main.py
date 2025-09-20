import cv2
import os

IMAGE_DIR = os.path.join(os.path.dirname(__file__), "images")
images = [os.path.join(IMAGE_DIR, x) for x in os.listdir(IMAGE_DIR)]

board = cv2.imread(images[0])
assert board is not None
cv2.imwrite("00_board.png", board)

gray = cv2.cvtColor(board, cv2.COLOR_BGR2HSV)
cv2.imwrite("01_hsv.png", gray)

blurred = cv2.GaussianBlur(gray, (11, 11), 4)
cv2.imwrite("02_blur.png", blurred)

canny = cv2.Canny(blurred, 20, 200)
cv2.imwrite("04_canny.png", canny)

ok, corners = cv2.findChessboardCorners(canny, (8, 8))
if ok:
    cv2.imwrite("99_corners.png", corners)
else:
    print("not ok!")
