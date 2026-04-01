# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file LICENSE.rst or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION ${CMAKE_VERSION}) # this file comes with cmake

# If CMAKE_DISABLE_SOURCE_CHANGES is set to true and the source directory is an
# existing directory in our source tree, calling file(MAKE_DIRECTORY) on it
# would cause a fatal error, even though it would be a no-op.
if(NOT EXISTS "C:/STM32/Capstone_MEMS_Testbench/Nucleo_H7S3L8/Appli")
  file(MAKE_DIRECTORY "C:/STM32/Capstone_MEMS_Testbench/Nucleo_H7S3L8/Appli")
endif()
file(MAKE_DIRECTORY
  "C:/STM32/Capstone_MEMS_Testbench/Nucleo_H7S3L8/Appli/build"
  "C:/STM32/Capstone_MEMS_Testbench/Nucleo_H7S3L8/build/Debug/Appli"
  "C:/STM32/Capstone_MEMS_Testbench/Nucleo_H7S3L8/build/Debug/Appli/tmp"
  "C:/STM32/Capstone_MEMS_Testbench/Nucleo_H7S3L8/build/Debug/Appli/src/Nucleo_H7S3L8_Appli-stamp"
  "C:/STM32/Capstone_MEMS_Testbench/Nucleo_H7S3L8/build/Debug/Appli/src"
  "C:/STM32/Capstone_MEMS_Testbench/Nucleo_H7S3L8/build/Debug/Appli/src/Nucleo_H7S3L8_Appli-stamp"
)

set(configSubDirs )
foreach(subDir IN LISTS configSubDirs)
    file(MAKE_DIRECTORY "C:/STM32/Capstone_MEMS_Testbench/Nucleo_H7S3L8/build/Debug/Appli/src/Nucleo_H7S3L8_Appli-stamp/${subDir}")
endforeach()
if(cfgdir)
  file(MAKE_DIRECTORY "C:/STM32/Capstone_MEMS_Testbench/Nucleo_H7S3L8/build/Debug/Appli/src/Nucleo_H7S3L8_Appli-stamp${cfgdir}") # cfgdir has leading slash
endif()
