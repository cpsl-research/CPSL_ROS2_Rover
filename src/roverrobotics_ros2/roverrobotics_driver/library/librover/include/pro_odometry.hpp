#pragma once

#include <cmath>

namespace RoverRobotics {

// Firmware build whose rpm feedback is half the wheel rpm (read x2).
constexpr int kProOvfFixedFirmVer = 10009;

// Wheel-odometry constants of the Rover Pro. The defaults are the single
// source of the values; with them the result is bit-identical to the
// original fixed constants (a multiply by 1.0 is exact).
struct ProOdomParams {
  double linear_scale = 1.0;       // multiplies linear and angular velocity
  double traction_factor = 0.610;  // angular factor (4WD default)
  double wheel_separation = 0.365; // m, center distance between the wheels
};

struct ProOdometry {
  double linear;
  double angular;
};

// Wheel rpm to body twist. rpm_to_mps_ratio is the driver's
// MOTOR_RPM_TO_MPS_RATIO_. Operation order follows the original code; the
// scale is applied to the finished value (the same as scaling each wheel).
inline ProOdometry pro_odometry(float rpm1, float rpm2, int firmware,
                                float rpm_to_mps_ratio,
                                const ProOdomParams& p) {
  const double angular_coef = 1 / p.wheel_separation;
  ProOdometry o;
  if (firmware == kProOvfFixedFirmVer) {
    o.linear = 0.5 * (rpm1 * 2 / rpm_to_mps_ratio + rpm2 * 2 / rpm_to_mps_ratio);
    o.angular = ((rpm2 * 2 / rpm_to_mps_ratio) - (rpm1 * 2 / rpm_to_mps_ratio)) *
                angular_coef * p.traction_factor;
  } else {
    o.linear = 0.5 * (rpm1 / rpm_to_mps_ratio + rpm2 / rpm_to_mps_ratio);
    o.angular = ((rpm2 / rpm_to_mps_ratio) - (rpm1 / rpm_to_mps_ratio)) *
                angular_coef * p.traction_factor;
  }
  o.linear *= p.linear_scale;
  o.angular *= p.linear_scale;
  return o;
}

}  // namespace RoverRobotics
