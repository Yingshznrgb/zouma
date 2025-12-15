import cv2

def open_camera():
    # 尝试打开摄像头设备（默认索引为0）
    cap = cv2.VideoCapture(0)

    # 检查摄像头是否成功打开
    if not cap.isOpened():
        print("无法打开摄像头，请确保已正确连接并启用摄像头模块")
        return

    print("摄像头已成功打开，按 'q' 键退出")

    while True:
        # 逐帧捕获画面
        ret, frame = cap.read()

        # 检查是否成功捕获画面
        if not ret:
            print("无法获取画面，退出...")
            break

        # 显示捕获的画面
        cv2.imshow('Raspberry Pi Camera', frame)

        # 按 'q' 键退出循环
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 释放摄像头并关闭所有窗口
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    open_camera()    