# Additional clean files
cmake_minimum_required(VERSION 3.16)

if("${CONFIG}" STREQUAL "" OR "${CONFIG}" STREQUAL "Debug")
  file(REMOVE_RECURSE
  "C:\\STM32\\Capstone_MEMS_Testbench\\Nucleo_H7S3L8\\Appli\\build"
  )
endif()
