import numpy as np

class ExtendedKalmanFilter:
    def __init__(self, initial_state, initial_covariance, process_noise, measurement_noise):
        """
        初始化扩展卡尔曼滤波器
        
        参数:
            initial_state (numpy.ndarray): 初始状态向量 [位置, 速度]
            initial_covariance (numpy.ndarray): 初始状态协方差矩阵
            process_noise (numpy.ndarray): 过程噪声协方差矩阵
            measurement_noise (numpy.ndarray): 测量噪声协方差矩阵
        """
        self.state = initial_state
        self.covariance = initial_covariance
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise

    def predict(self, control_input):
        """
        预测步骤：根据控制输入预测下一个状态
        
        参数:
            control_input (numpy.ndarray): 控制输入向量
        """
        # 状态转移矩阵 (假设简单的匀速运动模型)
        F = np.array([[1.0, 1.0], [0.0, 1.0]])
        
        # 控制输入矩阵 (假设控制输入直接影响加速度)
        B = np.array([0.5, 1.0])  # 对于位置和速度的影响
        
        # 预测状态
        self.state = F @ self.state + B * control_input
        
        # 预测协方差
        self.covariance = F @ self.covariance @ F.T + self.process_noise

    def update(self, measurement):
        """
        更新步骤：根据测量值更新状态估计
        
        参数:
            measurement (numpy.ndarray): 测量值向量
        """
        # 测量矩阵 (假设直接测量位置)
        H = np.array([[1.0, 0.0]])
        
        # 计算卡尔曼增益
        kalman_gain = self.covariance @ H.T @ np.linalg.inv(H @ self.covariance @ H.T + self.measurement_noise)
        
        # 更新状态
        self.state = self.state + kalman_gain @ (measurement - H @ self.state)
        
        # 更新协方差
        self.covariance = (np.eye(2) - kalman_gain @ H) @ self.covariance

    def get_state(self):
        """获取当前状态估计"""
        return self.state, self.covariance


# 使用示例
if __name__ == "__main__":
    # 输入参数
    initial_speed = 10.0  # 初始速度估计 (m/s)
    initial_position = 0.0  # 初始位置估计 (m)
    control_inputs = np.array([0.5, 1.0, 0.8, 1.2, 0.9])  # 控制输入序列 (加速度)
    measurements = np.array([2.0, 3.5, 5.8, 8.1, 10.4])  # 测量值序列 (位置)

    # 初始化滤波器
    initial_state = np.array([initial_position, initial_speed])
    initial_covariance = np.eye(2)  # 初始协方差矩阵
    process_noise = np.diag([0.1, 0.1])  # 过程噪声协方差矩阵
    measurement_noise = np.array([[0.5]])  # 测量噪声协方差矩阵

    for i in range(50):
        ekf = ExtendedKalmanFilter(initial_state, initial_covariance, process_noise, measurement_noise)

        # 模拟递推过程
        optimal_speed = []
        optimal_position = []
        optimal_covariance = []

        for uk, zk in zip(control_inputs, measurements):
            ekf.predict(uk)
            ekf.update(zk)
        
            state, covariance = ekf.get_state()
            optimal_speed.append(state[1])
            optimal_position.append(state[0])
            optimal_covariance.append(covariance)

        # 输出结果
        print("最优速度估计序列:", optimal_speed)
        print("最优位置估计序列:", optimal_position)
        print("最优协方差序列:", optimal_covariance)