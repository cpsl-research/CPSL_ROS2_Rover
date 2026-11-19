#pragma once

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <mutex>
#include <thread>

namespace RoverRobotics {

/*
 * @brief Shutdown flag shared by an object and the worker threads it owns.
 * A worker loop runs `while (!stop.requested())` and paces itself with
 * `if (stop.wait_for(ms)) break;` instead of sleep_for, so request() wakes
 * it at once rather than after its sleep interval. The owning object's
 * destructor calls request() and then joins its threads before any member
 * those threads use is destroyed.
 */
class StopSignal {
 public:
  void request() {
    {
      std::lock_guard<std::mutex> lock(mutex_);
      stop_ = true;
    }
    cv_.notify_all();
  }

  bool requested() const { return stop_.load(); }

  /* Wait up to `ms` milliseconds. Returns true if stop was requested. */
  bool wait_for(int ms) {
    std::unique_lock<std::mutex> lock(mutex_);
    return cv_.wait_for(lock, std::chrono::milliseconds(ms),
                        [this] { return stop_.load(); });
  }

 private:
  std::atomic<bool> stop_{false};
  std::mutex mutex_;
  std::condition_variable cv_;
};

inline void join_if_joinable(std::thread &t) {
  if (t.joinable()) t.join();
}

}  // namespace RoverRobotics
