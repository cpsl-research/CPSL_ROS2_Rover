#include <gtest/gtest.h>

#include <vector>

#include "pro_odometry.hpp"

using RoverRobotics::ProOdomParams;
using RoverRobotics::pro_odometry;

namespace {
// Same expression as protocol_pro.hpp: MOTOR_RPM_TO_MPS_RATIO_.
const float kGear = 1.0 / 192.0;
const float kDist = 0.8179;
const float kRatio = 1 / (kGear * kDist / 60.0);

// Verbatim copy of the original odometry code (fixed constants).
void original(float m1, float m2, int firmware, double& lin, double& ang) {
  const double wheel2wheelDistance = 0.365;
  const double odom_angular_coef_ = 1 / wheel2wheelDistance;
  const double odom_traction_factor_ = 0.610;
  const float MOTOR_RPM_TO_MPS_RATIO_ = kRatio;
  if (firmware == 10009) {
    lin = 0.5 * (m1 * 2 / MOTOR_RPM_TO_MPS_RATIO_ +
                 m2 * 2 / MOTOR_RPM_TO_MPS_RATIO_);
    ang = ((m2 * 2 / MOTOR_RPM_TO_MPS_RATIO_) -
           (m1 * 2 / MOTOR_RPM_TO_MPS_RATIO_)) *
          odom_angular_coef_ * odom_traction_factor_;
  } else {
    lin = 0.5 * (m1 / MOTOR_RPM_TO_MPS_RATIO_ + m2 / MOTOR_RPM_TO_MPS_RATIO_);
    ang = ((m2 / MOTOR_RPM_TO_MPS_RATIO_) - (m1 / MOTOR_RPM_TO_MPS_RATIO_)) *
          odom_angular_coef_ * odom_traction_factor_;
  }
}

const std::vector<float> kRpm = {0.f,   1.f,    -1.f,  0.37f, -12.5f, 40.f,
                                 -40.f, 123.4f, -250.f, 999.f, -3000.f, 1e5f};
const std::vector<int> kFirmware = {10009, 10008, 0, 12345};
}  // namespace

TEST(ProOdometry, DefaultsAreBitIdenticalToOriginal) {
  ProOdomParams defaults;
  for (int fw : kFirmware)
    for (float a : kRpm)
      for (float b : kRpm) {
        double lin, ang;
        original(a, b, fw, lin, ang);
        auto o = pro_odometry(a, b, fw, kRatio, defaults);
        EXPECT_EQ(o.linear, lin) << a << " " << b << " " << fw;
        EXPECT_EQ(o.angular, ang) << a << " " << b << " " << fw;
      }
}

TEST(ProOdometry, CalibratedParamsScaleLinearAndAngular) {
  ProOdomParams cal;
  cal.linear_scale = 1.94;
  cal.traction_factor = 0.645;
  cal.wheel_separation = 0.365;
  const double ang_gain = 1.94 * 0.645 / 0.610;
  for (int fw : kFirmware)
    for (float a : kRpm)
      for (float b : kRpm) {
        double lin, ang;
        original(a, b, fw, lin, ang);
        auto o = pro_odometry(a, b, fw, kRatio, cal);
        EXPECT_NEAR(o.linear, lin * 1.94, 1e-9 * std::abs(lin * 1.94) + 1e-300);
        EXPECT_NEAR(o.angular, ang * ang_gain,
                    1e-9 * std::abs(ang * ang_gain) + 1e-300);
      }
}
