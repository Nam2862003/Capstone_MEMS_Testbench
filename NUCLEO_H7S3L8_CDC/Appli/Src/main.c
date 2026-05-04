/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "usb_device.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "usbd_cdc_if.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
#define DDS_CS_GPIO_Port GPIOD
#define DDS_CS_Pin GPIO_PIN_14
#define PE_PR_SEL_GPIO_Port GPIOE
#define PE_PR_SEL_Pin GPIO_PIN_9
#define ACTSRC_GPIO_Port GPIOE
#define ACTSRC_Pin GPIO_PIN_11
#define BNC_ADC_GPIO_Port GPIOE
#define BNC_ADC_Pin GPIO_PIN_15
#define PE_GAIN_A0_GPIO_Port GPIOE
#define PE_GAIN_A0_Pin GPIO_PIN_13
#define PE_GAIN_A1_GPIO_Port GPIOE
#define PE_GAIN_A1_Pin GPIO_PIN_8

#define AD9833_CTRL_B28 0x2000U
#define AD9833_CTRL_RESET 0x0100U
#define AD9833_CTRL_SLEEP1 0x0080U
#define AD9833_FREQ0_REG 0x4000U
#define AD9833_MCLK_HZ 25000000.0

#define BOARD_MODE_PE 0U
#define BOARD_MODE_PR 1U

#define ACTUATOR_MODE_NONE 0U
#define ACTUATOR_MODE_DDS 1U
#define ACTUATOR_MODE_FUNCTION_GENERATOR 2U
#define ACTUATOR_MODE_STM32_DAC 3U

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
ADC_HandleTypeDef hadc1;
ADC_HandleTypeDef hadc2;
DMA_NodeTypeDef Node_GPDMA1_Channel0 __attribute__((section("noncacheable_buffer")));
DMA_QListTypeDef List_GPDMA1_Channel0;
DMA_HandleTypeDef handle_GPDMA1_Channel0;

I2C_HandleTypeDef hi2c3;

SPI_HandleTypeDef hspi1;

TIM_HandleTypeDef htim6;

/* USER CODE BEGIN PV */
#define Max_ADC_BUFFER_SIZE 4096 // 128kB buffer, can hold 16384 samples of 2 ADCs (32 bits each)  
__attribute__((section("noncacheable_buffer"), aligned(32)))
uint32_t adc_buffer[Max_ADC_BUFFER_SIZE];
volatile uint32_t active_buffer_size = Max_ADC_BUFFER_SIZE;
volatile uint8_t adc_running = 0;
#define CHUNK_SIZE 1024 // Number of 32-bit words to send in one USB packet, must be less than (USB_MAX_PACKET_SIZE / 4) to fit in one packet
volatile uint8_t dma_half_complete = 0;
volatile uint8_t dma_full_complete = 0;
uint16_t adc1, adc2;
static volatile uint8_t adc_stream_enabled = 0U;
static char usb_command_buffer[96];
static uint32_t usb_command_length;
static volatile uint8_t dds_running = 0U;
static volatile uint32_t dds_frequency_hz = 1000U;
static volatile uint8_t board_mode = BOARD_MODE_PE;
static volatile uint8_t actuator_mode = ACTUATOR_MODE_DDS;
static volatile uint8_t pe_gain_index = 0U;

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
static void MPU_Config(void);
static void MX_GPIO_Init(void);
static void MX_GPDMA1_Init(void);
static void MX_I2C3_Init(void);
static void MX_UCPD1_Init(void);
static void MX_ADC1_Init(void);
static void MX_ADC2_Init(void);
static void MX_TIM6_Init(void);
static void MX_SPI1_Init(void);
/* USER CODE BEGIN PFP */
static void CDC_SendBytes(uint8_t *data, uint16_t length);
static void CDC_SendText(const char *text);
static void SendAdcBinaryFrame(uint32_t start_index, uint32_t sample_count);
static void ProcessUsbCommand(const char *command);
static void StartAdcAcquisition(void);
static void StopAdcAcquisition(void);
static void SetAdcBufferSize(uint32_t requested_size);
static void SetAdcSamplingRate(uint32_t sample_rate_hz);
static void SetAdcResolution(uint32_t resolution_bits);
static uint8_t IsCompleteUsbCommand(const char *command);
static void DdsInit(void);
static void DdsStart(void);
static void DdsStop(void);
static void DdsSetFrequency(float freq_hz);
static void SetBoardMode(uint8_t mode);
static void SetActuatorMode(uint8_t mode);
static void SetPeGain(uint8_t gain_index);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MPU Configuration--------------------------------------------------------*/
  MPU_Config();

  /* Enable the CPU Cache */

  /* Enable I-Cache---------------------------------------------------------*/
  SCB_EnableICache();

  /* Enable D-Cache---------------------------------------------------------*/
  SCB_EnableDCache();

  /* MCU Configuration--------------------------------------------------------*/

  /* Update SystemCoreClock variable according to RCC registers values. */
  SystemCoreClockUpdate();

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_GPDMA1_Init();
  MX_I2C3_Init();
  MX_UCPD1_Init();
  MX_USB_DEVICE_Init();
  MX_ADC1_Init();
  MX_ADC2_Init();
  MX_TIM6_Init();
  MX_SPI1_Init();
  /* USER CODE BEGIN 2 */
  HAL_ADC_Stop(&hadc1);
  HAL_ADC_Stop(&hadc2);
  /* Calibrate ADC1 (Master) */
  if (HAL_ADCEx_Calibration_Start(&hadc1, ADC_SINGLE_ENDED) != HAL_OK)
  {
      Error_Handler();
  }

  /* Calibrate ADC2 (Slave) */
  if (HAL_ADCEx_Calibration_Start(&hadc2, ADC_SINGLE_ENDED) != HAL_OK)
  {
      Error_Handler();
  }

  /* ADC streaming starts only after the GUI sends START ADC. */
  DdsInit();
  SetBoardMode(BOARD_MODE_PE);
  SetActuatorMode(ACTUATOR_MODE_DDS);
  SetPeGain(0U);

  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
        if (dma_half_complete != 0U)
    {
      dma_half_complete = 0U;
      if (adc_stream_enabled != 0U)
      {
        SendAdcBinaryFrame(0U, active_buffer_size / 2U);
      }
    }

    if (dma_full_complete != 0U)
    {
      dma_full_complete = 0U;
      if (adc_stream_enabled != 0U)
      {
        SendAdcBinaryFrame(active_buffer_size / 2U, active_buffer_size / 2U);
      }
    }
  }
  /* USER CODE END 3 */
}

/**
  * @brief ADC1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_ADC1_Init(void)
{

  /* USER CODE BEGIN ADC1_Init 0 */

  /* USER CODE END ADC1_Init 0 */

  ADC_MultiModeTypeDef multimode = {0};
  ADC_ChannelConfTypeDef sConfig = {0};

  /* USER CODE BEGIN ADC1_Init 1 */

  /* USER CODE END ADC1_Init 1 */

  /** Common config
  */
  hadc1.Instance = ADC1;
  hadc1.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV4;
  hadc1.Init.Resolution = ADC_RESOLUTION_12B;
  hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
  hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
  hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
  hadc1.Init.LowPowerAutoWait = DISABLE;
  hadc1.Init.ContinuousConvMode = DISABLE;
  hadc1.Init.NbrOfConversion = 1;
  hadc1.Init.DiscontinuousConvMode = DISABLE;
  hadc1.Init.ExternalTrigConv = ADC_EXTERNALTRIG_T6_TRGO;
  hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_RISING;
  hadc1.Init.SamplingMode = ADC_SAMPLING_MODE_NORMAL;
  hadc1.Init.ConversionDataManagement = ADC_CONVERSIONDATA_DMA_CIRCULAR;
  hadc1.Init.Overrun = ADC_OVR_DATA_PRESERVED;
  hadc1.Init.OversamplingMode = DISABLE;
  if (HAL_ADC_Init(&hadc1) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure the ADC multi-mode
  */
  multimode.Mode = ADC_DUALMODE_REGSIMULT;
  multimode.DMAAccessMode = ADC_DMAACCESSMODE_12_10_BITS;
  multimode.TwoSamplingDelay = ADC_TWOSAMPLINGDELAY_1CYCLE;
  if (HAL_ADCEx_MultiModeConfigChannel(&hadc1, &multimode) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Regular Channel
  */
  sConfig.Channel = ADC_CHANNEL_15;
  sConfig.Rank = ADC_REGULAR_RANK_1;
  sConfig.SamplingTime = ADC_SAMPLETIME_2CYCLES_5;
  sConfig.SingleDiff = ADC_SINGLE_ENDED;
  sConfig.OffsetNumber = ADC_OFFSET_NONE;
  sConfig.Offset = 0;
  sConfig.OffsetSign = ADC_OFFSET_SIGN_NEGATIVE;
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN ADC1_Init 2 */

  /* USER CODE END ADC1_Init 2 */

}

/**
  * @brief ADC2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_ADC2_Init(void)
{

  /* USER CODE BEGIN ADC2_Init 0 */

  /* USER CODE END ADC2_Init 0 */

  ADC_ChannelConfTypeDef sConfig = {0};

  /* USER CODE BEGIN ADC2_Init 1 */

  /* USER CODE END ADC2_Init 1 */

  /** Common config
  */
  hadc2.Instance = ADC2;
  hadc2.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV4;
  hadc2.Init.Resolution = ADC_RESOLUTION_12B;
  hadc2.Init.DataAlign = ADC_DATAALIGN_RIGHT;
  hadc2.Init.ScanConvMode = ADC_SCAN_DISABLE;
  hadc2.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
  hadc2.Init.LowPowerAutoWait = DISABLE;
  hadc2.Init.ContinuousConvMode = DISABLE;
  hadc2.Init.NbrOfConversion = 1;
  hadc2.Init.DiscontinuousConvMode = DISABLE;
  hadc2.Init.SamplingMode = ADC_SAMPLING_MODE_NORMAL;
  hadc2.Init.ConversionDataManagement = ADC_CONVERSIONDATA_DR;
  hadc2.Init.Overrun = ADC_OVR_DATA_PRESERVED;
  hadc2.Init.OversamplingMode = DISABLE;
  if (HAL_ADC_Init(&hadc2) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Regular Channel
  */
  sConfig.Channel = ADC_CHANNEL_4;
  sConfig.Rank = ADC_REGULAR_RANK_1;
  sConfig.SamplingTime = ADC_SAMPLETIME_2CYCLES_5;
  sConfig.SingleDiff = ADC_SINGLE_ENDED;
  sConfig.OffsetNumber = ADC_OFFSET_NONE;
  sConfig.Offset = 0;
  sConfig.OffsetSign = ADC_OFFSET_SIGN_NEGATIVE;
  if (HAL_ADC_ConfigChannel(&hadc2, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN ADC2_Init 2 */

  /* USER CODE END ADC2_Init 2 */

}

/**
  * @brief GPDMA1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPDMA1_Init(void)
{

  /* USER CODE BEGIN GPDMA1_Init 0 */

  /* USER CODE END GPDMA1_Init 0 */

  /* Peripheral clock enable */
  __HAL_RCC_GPDMA1_CLK_ENABLE();

  /* GPDMA1 interrupt Init */
    HAL_NVIC_SetPriority(GPDMA1_Channel0_IRQn, 0, 0);
    HAL_NVIC_EnableIRQ(GPDMA1_Channel0_IRQn);
    HAL_NVIC_SetPriority(GPDMA1_Channel1_IRQn, 0, 0);
    HAL_NVIC_EnableIRQ(GPDMA1_Channel1_IRQn);
    HAL_NVIC_SetPriority(GPDMA1_Channel2_IRQn, 0, 0);
    HAL_NVIC_EnableIRQ(GPDMA1_Channel2_IRQn);

  /* USER CODE BEGIN GPDMA1_Init 1 */

  /* USER CODE END GPDMA1_Init 1 */
  /* USER CODE BEGIN GPDMA1_Init 2 */

  /* USER CODE END GPDMA1_Init 2 */

}

/**
  * @brief I2C3 Initialization Function
  * @param None
  * @retval None
  */
static void MX_I2C3_Init(void)
{

  /* USER CODE BEGIN I2C3_Init 0 */

  /* USER CODE END I2C3_Init 0 */

  /* USER CODE BEGIN I2C3_Init 1 */

  /* USER CODE END I2C3_Init 1 */
  hi2c3.Instance = I2C3;
  hi2c3.Init.Timing = 0x20C0EDFF;
  hi2c3.Init.OwnAddress1 = 0;
  hi2c3.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hi2c3.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hi2c3.Init.OwnAddress2 = 0;
  hi2c3.Init.OwnAddress2Masks = I2C_OA2_NOMASK;
  hi2c3.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hi2c3.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
  if (HAL_I2C_Init(&hi2c3) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Analogue filter
  */
  if (HAL_I2CEx_ConfigAnalogFilter(&hi2c3, I2C_ANALOGFILTER_ENABLE) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Digital filter
  */
  if (HAL_I2CEx_ConfigDigitalFilter(&hi2c3, 0) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN I2C3_Init 2 */

  /* USER CODE END I2C3_Init 2 */

}

/**
  * @brief SPI1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_SPI1_Init(void)
{

  /* USER CODE BEGIN SPI1_Init 0 */

  /* USER CODE END SPI1_Init 0 */

  /* USER CODE BEGIN SPI1_Init 1 */

  /* USER CODE END SPI1_Init 1 */
  /* SPI1 parameter configuration*/
  hspi1.Instance = SPI1;
  hspi1.Init.Mode = SPI_MODE_MASTER;
  hspi1.Init.Direction = SPI_DIRECTION_2LINES_TXONLY;
  hspi1.Init.DataSize = SPI_DATASIZE_8BIT;
  hspi1.Init.CLKPolarity = SPI_POLARITY_LOW;
  hspi1.Init.CLKPhase = SPI_PHASE_1EDGE;
  hspi1.Init.NSS = SPI_NSS_SOFT;
  hspi1.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_64;
  hspi1.Init.FirstBit = SPI_FIRSTBIT_MSB;
  hspi1.Init.TIMode = SPI_TIMODE_DISABLE;
  hspi1.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
  hspi1.Init.CRCPolynomial = 0x7;
  hspi1.Init.NSSPMode = SPI_NSS_PULSE_ENABLE;
  hspi1.Init.NSSPolarity = SPI_NSS_POLARITY_LOW;
  hspi1.Init.FifoThreshold = SPI_FIFO_THRESHOLD_01DATA;
  hspi1.Init.MasterSSIdleness = SPI_MASTER_SS_IDLENESS_00CYCLE;
  hspi1.Init.MasterInterDataIdleness = SPI_MASTER_INTERDATA_IDLENESS_00CYCLE;
  hspi1.Init.MasterReceiverAutoSusp = SPI_MASTER_RX_AUTOSUSP_DISABLE;
  hspi1.Init.MasterKeepIOState = SPI_MASTER_KEEP_IO_STATE_DISABLE;
  hspi1.Init.IOSwap = SPI_IO_SWAP_DISABLE;
  hspi1.Init.ReadyMasterManagement = SPI_RDY_MASTER_MANAGEMENT_INTERNALLY;
  hspi1.Init.ReadyPolarity = SPI_RDY_POLARITY_HIGH;
  if (HAL_SPI_Init(&hspi1) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN SPI1_Init 2 */

  /* USER CODE END SPI1_Init 2 */

}

/**
  * @brief TIM6 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM6_Init(void)
{

  /* USER CODE BEGIN TIM6_Init 0 */

  /* USER CODE END TIM6_Init 0 */

  TIM_MasterConfigTypeDef sMasterConfig = {0};

  /* USER CODE BEGIN TIM6_Init 1 */

  /* USER CODE END TIM6_Init 1 */
  htim6.Instance = TIM6;
  htim6.Init.Prescaler = 3-1;
  htim6.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim6.Init.Period = 49;
  htim6.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim6) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_UPDATE;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim6, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM6_Init 2 */

  /* USER CODE END TIM6_Init 2 */

}

/**
  * @brief UCPD1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_UCPD1_Init(void)
{

  /* USER CODE BEGIN UCPD1_Init 0 */

  /* USER CODE END UCPD1_Init 0 */

  LL_GPIO_InitTypeDef GPIO_InitStruct = {0};
  LL_DMA_InitTypeDef DMA_InitStruct = {0};

  /* Peripheral clock enable */
  LL_APB1_GRP2_EnableClock(LL_APB1_GRP2_PERIPH_UCPD1);

  LL_AHB4_GRP1_EnableClock(LL_AHB4_GRP1_PERIPH_GPIOM);
  /**UCPD1 GPIO Configuration
  PM1   ------> UCPD1_CC2
  PM0   ------> UCPD1_CC1
  */
  GPIO_InitStruct.Pin = LL_GPIO_PIN_1|LL_GPIO_PIN_0;
  GPIO_InitStruct.Mode = LL_GPIO_MODE_ANALOG;
  GPIO_InitStruct.Pull = LL_GPIO_PULL_NO;
  LL_GPIO_Init(GPIOM, &GPIO_InitStruct);

  /* UCPD1 DMA Init */

  /* GPDMA1_REQUEST_UCPD1_TX Init */
  DMA_InitStruct.SrcAddress = 0x00000000U;
  DMA_InitStruct.DestAddress = 0x00000000U;
  DMA_InitStruct.Direction = LL_DMA_DIRECTION_PERIPH_TO_MEMORY;
  DMA_InitStruct.BlkHWRequest = LL_DMA_HWREQUEST_SINGLEBURST;
  DMA_InitStruct.DataAlignment = LL_DMA_DATA_ALIGN_ZEROPADD;
  DMA_InitStruct.SrcBurstLength = 1;
  DMA_InitStruct.DestBurstLength = 1;
  DMA_InitStruct.SrcDataWidth = LL_DMA_SRC_DATAWIDTH_BYTE;
  DMA_InitStruct.DestDataWidth = LL_DMA_DEST_DATAWIDTH_BYTE;
  DMA_InitStruct.SrcIncMode = LL_DMA_SRC_FIXED;
  DMA_InitStruct.DestIncMode = LL_DMA_DEST_FIXED;
  DMA_InitStruct.Priority = LL_DMA_LOW_PRIORITY_LOW_WEIGHT;
  DMA_InitStruct.BlkDataLength = 0x00000000U;
  DMA_InitStruct.TriggerMode = LL_DMA_TRIGM_BLK_TRANSFER;
  DMA_InitStruct.TriggerPolarity = LL_DMA_TRIG_POLARITY_MASKED;
  DMA_InitStruct.TriggerSelection = 0x00000000U;
  DMA_InitStruct.Request = LL_GPDMA1_REQUEST_UCPD1_TX;
  DMA_InitStruct.TransferEventMode = LL_DMA_TCEM_BLK_TRANSFER;
  DMA_InitStruct.SrcAllocatedPort = LL_DMA_SRC_ALLOCATED_PORT0;
  DMA_InitStruct.DestAllocatedPort = LL_DMA_DEST_ALLOCATED_PORT0;
  DMA_InitStruct.LinkAllocatedPort = LL_DMA_LINK_ALLOCATED_PORT1;
  DMA_InitStruct.LinkStepMode = LL_DMA_LSM_FULL_EXECUTION;
  DMA_InitStruct.LinkedListBaseAddr = 0x00000000U;
  DMA_InitStruct.LinkedListAddrOffset = 0x00000000U;
  LL_DMA_Init(GPDMA1, LL_DMA_CHANNEL_2, &DMA_InitStruct);

  /* GPDMA1_REQUEST_UCPD1_RX Init */
  DMA_InitStruct.SrcAddress = 0x00000000U;
  DMA_InitStruct.DestAddress = 0x00000000U;
  DMA_InitStruct.Direction = LL_DMA_DIRECTION_PERIPH_TO_MEMORY;
  DMA_InitStruct.BlkHWRequest = LL_DMA_HWREQUEST_SINGLEBURST;
  DMA_InitStruct.DataAlignment = LL_DMA_DATA_ALIGN_ZEROPADD;
  DMA_InitStruct.SrcBurstLength = 1;
  DMA_InitStruct.DestBurstLength = 1;
  DMA_InitStruct.SrcDataWidth = LL_DMA_SRC_DATAWIDTH_BYTE;
  DMA_InitStruct.DestDataWidth = LL_DMA_DEST_DATAWIDTH_BYTE;
  DMA_InitStruct.SrcIncMode = LL_DMA_SRC_FIXED;
  DMA_InitStruct.DestIncMode = LL_DMA_DEST_FIXED;
  DMA_InitStruct.Priority = LL_DMA_LOW_PRIORITY_LOW_WEIGHT;
  DMA_InitStruct.BlkDataLength = 0x00000000U;
  DMA_InitStruct.TriggerMode = LL_DMA_TRIGM_BLK_TRANSFER;
  DMA_InitStruct.TriggerPolarity = LL_DMA_TRIG_POLARITY_MASKED;
  DMA_InitStruct.TriggerSelection = 0x00000000U;
  DMA_InitStruct.Request = LL_GPDMA1_REQUEST_UCPD1_RX;
  DMA_InitStruct.TransferEventMode = LL_DMA_TCEM_BLK_TRANSFER;
  DMA_InitStruct.SrcAllocatedPort = LL_DMA_SRC_ALLOCATED_PORT0;
  DMA_InitStruct.DestAllocatedPort = LL_DMA_DEST_ALLOCATED_PORT0;
  DMA_InitStruct.LinkAllocatedPort = LL_DMA_LINK_ALLOCATED_PORT1;
  DMA_InitStruct.LinkStepMode = LL_DMA_LSM_FULL_EXECUTION;
  DMA_InitStruct.LinkedListBaseAddr = 0x00000000U;
  DMA_InitStruct.LinkedListAddrOffset = 0x00000000U;
  LL_DMA_Init(GPDMA1, LL_DMA_CHANNEL_1, &DMA_InitStruct);

  /* UCPD1 interrupt Init */
  NVIC_SetPriority(UCPD1_IRQn, NVIC_EncodePriority(NVIC_GetPriorityGrouping(),0, 0));
  NVIC_EnableIRQ(UCPD1_IRQn);

  /* USER CODE BEGIN UCPD1_Init 1 */

  /* USER CODE END UCPD1_Init 1 */
  /* USER CODE BEGIN UCPD1_Init 2 */

  /* USER CODE END UCPD1_Init 2 */

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  /* USER CODE BEGIN MX_GPIO_Init_1 */

  /* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOF_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOM_CLK_ENABLE();
  __HAL_RCC_GPIOE_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOF, GPIO_PIN_3, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOM, GPIO_PIN_9, GPIO_PIN_SET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOE, GPIO_PIN_13|GPIO_PIN_11|GPIO_PIN_15|GPIO_PIN_7
                          |GPIO_PIN_9|GPIO_PIN_8, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOD, GPIO_PIN_14, GPIO_PIN_SET);

  /*Configure GPIO pin : PF3 */
  GPIO_InitStruct.Pin = GPIO_PIN_3;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOF, &GPIO_InitStruct);

  /*Configure GPIO pin : PM9 */
  GPIO_InitStruct.Pin = GPIO_PIN_9;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOM, &GPIO_InitStruct);

  /*Configure GPIO pins : PE13 PE11 PE15 PE7
                           PE9 PE8 */
  GPIO_InitStruct.Pin = GPIO_PIN_13|GPIO_PIN_11|GPIO_PIN_15|GPIO_PIN_7
                          |GPIO_PIN_9|GPIO_PIN_8;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOE, &GPIO_InitStruct);

  /*Configure GPIO pin : PD14 */
  GPIO_InitStruct.Pin = GPIO_PIN_14;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStruct);

  /* USER CODE BEGIN MX_GPIO_Init_2 */
  HAL_GPIO_WritePin(GPIOM, GPIO_PIN_9, GPIO_PIN_SET);

  GPIO_InitStruct.Pin = GPIO_PIN_9;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOM, &GPIO_InitStruct);

  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */
static void DdsWriteWord(uint16_t word)
{
  uint8_t tx[2];

  tx[0] = (uint8_t)((word >> 8U) & 0xFFU);
  tx[1] = (uint8_t)(word & 0xFFU);

  HAL_GPIO_WritePin(DDS_CS_GPIO_Port, DDS_CS_Pin, GPIO_PIN_RESET);
  (void)HAL_SPI_Transmit(&hspi1, tx, 2U, HAL_MAX_DELAY);
  HAL_GPIO_WritePin(DDS_CS_GPIO_Port, DDS_CS_Pin, GPIO_PIN_SET);
}

static void DdsApplyFrequencyWord(uint32_t freq_word)
{
  uint16_t lsb_word = AD9833_FREQ0_REG | (uint16_t)(freq_word & 0x3FFFU);
  uint16_t msb_word = AD9833_FREQ0_REG | (uint16_t)((freq_word >> 14U) & 0x3FFFU);

  DdsWriteWord(AD9833_CTRL_B28 | AD9833_CTRL_RESET);
  DdsWriteWord(lsb_word);
  DdsWriteWord(msb_word);

  if (dds_running != 0U)
  {
    DdsWriteWord(AD9833_CTRL_B28);
  }
  else
  {
    DdsWriteWord(AD9833_CTRL_B28 | AD9833_CTRL_RESET | AD9833_CTRL_SLEEP1);
  }
}

static void DdsInit(void)
{
  HAL_GPIO_WritePin(DDS_CS_GPIO_Port, DDS_CS_Pin, GPIO_PIN_SET);
  dds_running = 0U;
  DdsApplyFrequencyWord(0U);
  DdsSetFrequency((float)dds_frequency_hz);
}

static void DdsStart(void)
{
  dds_running = 1U;
  DdsSetFrequency((float)dds_frequency_hz);
}

static void DdsStop(void)
{
  dds_running = 0U;
  DdsWriteWord(AD9833_CTRL_B28 | AD9833_CTRL_RESET | AD9833_CTRL_SLEEP1);
}

static void DdsSetFrequency(float freq_hz)
{
  double tuning;

  if (freq_hz < 0.0f)
  {
    return;
  }

  tuning = ((double)freq_hz * 268435456.0) / AD9833_MCLK_HZ;
  if (tuning > 268435455.0)
  {
    tuning = 268435455.0;
  }

  dds_frequency_hz = (uint32_t)(freq_hz + 0.5f);
  DdsApplyFrequencyWord((uint32_t)(tuning + 0.5));
}

static void SetBoardMode(uint8_t mode)
{
  board_mode = mode;

  if (mode == BOARD_MODE_PR)
  {
    HAL_GPIO_WritePin(PE_PR_SEL_GPIO_Port, PE_PR_SEL_Pin, GPIO_PIN_SET);
  }
  else
  {
    board_mode = BOARD_MODE_PE;
    HAL_GPIO_WritePin(PE_PR_SEL_GPIO_Port, PE_PR_SEL_Pin, GPIO_PIN_RESET);
  }
}

static void SetActuatorMode(uint8_t mode)
{
  actuator_mode = mode;

  switch (mode)
  {
    case ACTUATOR_MODE_FUNCTION_GENERATOR:
      HAL_GPIO_WritePin(ACTSRC_GPIO_Port, ACTSRC_Pin, GPIO_PIN_RESET);
      HAL_GPIO_WritePin(BNC_ADC_GPIO_Port, BNC_ADC_Pin, GPIO_PIN_SET);
      break;

    case ACTUATOR_MODE_DDS:
      HAL_GPIO_WritePin(ACTSRC_GPIO_Port, ACTSRC_Pin, GPIO_PIN_SET);
      HAL_GPIO_WritePin(BNC_ADC_GPIO_Port, BNC_ADC_Pin, GPIO_PIN_RESET);
      break;

    case ACTUATOR_MODE_STM32_DAC:
    default:
      actuator_mode = ACTUATOR_MODE_STM32_DAC;
      HAL_GPIO_WritePin(ACTSRC_GPIO_Port, ACTSRC_Pin, GPIO_PIN_RESET);
      HAL_GPIO_WritePin(BNC_ADC_GPIO_Port, BNC_ADC_Pin, GPIO_PIN_RESET);
      break;
  }
}

static void SetPeGain(uint8_t gain_index)
{
  uint8_t a0_state;
  uint8_t a1_state;

  if (gain_index > 3U)
  {
    return;
  }

  pe_gain_index = gain_index;
  a0_state = (uint8_t)(gain_index & 0x01U);
  a1_state = (uint8_t)((gain_index >> 1U) & 0x01U);

  HAL_GPIO_WritePin(PE_GAIN_A0_GPIO_Port,
                    PE_GAIN_A0_Pin,
                    (a0_state != 0U) ? GPIO_PIN_SET : GPIO_PIN_RESET);
  HAL_GPIO_WritePin(PE_GAIN_A1_GPIO_Port,
                    PE_GAIN_A1_Pin,
                    (a1_state != 0U) ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

static void CDC_SendBytes(uint8_t *data, uint16_t length)
{
  uint32_t start_tick = HAL_GetTick();

  while (CDC_Transmit_HS(data, length) == USBD_BUSY)
  {
    if ((HAL_GetTick() - start_tick) > 50U)
    {
      return;
    }
  }
}

static void CDC_SendText(const char *text)
{
  if (text == NULL)
  {
    return;
  }

  CDC_SendBytes((uint8_t *)text, (uint16_t)strlen(text));
}

static void SendAdcBinaryFrame(uint32_t start_index, uint32_t sample_count)
{
  uint8_t header[8];
  uint32_t offset = 0U;

  header[0] = 'A';
  header[1] = 'D';
  header[2] = 'C';
  header[3] = 'B';
  header[4] = (uint8_t)(sample_count & 0xFFU);
  header[5] = (uint8_t)((sample_count >> 8U) & 0xFFU);
  header[6] = 0U;
  header[7] = 0U;
  CDC_SendBytes(header, sizeof(header));

  while (offset < sample_count)
  {
    uint32_t chunk_words = sample_count - offset;

    if (chunk_words > CHUNK_SIZE)
    {
      chunk_words = CHUNK_SIZE;
    }

    CDC_SendBytes((uint8_t *)&adc_buffer[start_index + offset],
                  (uint16_t)(chunk_words * sizeof(uint32_t)));
    offset += chunk_words;
  }
}

static void StopAdcAcquisition(void)
{
  HAL_TIM_Base_Stop(&htim6);
  HAL_ADCEx_MultiModeStop_DMA(&hadc1);
  HAL_ADC_Stop(&hadc2);
  dma_half_complete = 0U;
  dma_full_complete = 0U;
  adc_running = 0U;
}

static void StartAdcAcquisition(void)
{
  dma_half_complete = 0U;
  dma_full_complete = 0U;

  if (HAL_ADC_Start(&hadc2) != HAL_OK)
  {
    Error_Handler();
  }

  if (HAL_ADCEx_MultiModeStart_DMA(&hadc1, (uint32_t *)adc_buffer, active_buffer_size) != HAL_OK)
  {
    Error_Handler();
  }

  if (HAL_TIM_Base_Start(&htim6) != HAL_OK)
  {
    Error_Handler();
  }

  adc_running = 1U;
}

static void SetAdcBufferSize(uint32_t requested_size)
{
  uint8_t was_running = adc_running;

  if ((requested_size < 2U) || (requested_size > Max_ADC_BUFFER_SIZE))
  {
    return;
  }

  if ((requested_size & 1U) != 0U)
  {
    requested_size--;
  }

  if (was_running != 0U)
  {
    StopAdcAcquisition();
  }

  active_buffer_size = requested_size;

  if (was_running != 0U)
  {
    StartAdcAcquisition();
  }
}

static void SetAdcSamplingRate(uint32_t sample_rate_hz)
{
  uint32_t timer_clock_hz;
  uint32_t prescaler;
  uint32_t timer_count_hz;
  uint32_t period;
  uint8_t was_running = adc_running;

  if ((sample_rate_hz < 1000U) || (sample_rate_hz > 3000000U))
  {
    return;
  }

  timer_clock_hz = HAL_RCC_GetPCLK1Freq();
  prescaler = htim6.Init.Prescaler + 1U;
  timer_count_hz = timer_clock_hz / prescaler;
  period = (timer_count_hz / sample_rate_hz);

  if ((period == 0U) || (period > 65536U))
  {
    return;
  }

  if (was_running != 0U)
  {
    StopAdcAcquisition();
  }

  htim6.Init.Period = period - 1U;
  if (HAL_TIM_Base_Init(&htim6) != HAL_OK)
  {
    Error_Handler();
  }
  __HAL_TIM_SET_COUNTER(&htim6, 0U);

  if (was_running != 0U)
  {
    StartAdcAcquisition();
  }
}

static void SetAdcResolution(uint32_t resolution_bits)
{
  ADC_MultiModeTypeDef multimode = {0};
  ADC_ChannelConfTypeDef sConfig = {0};
  uint32_t resolution;
  uint8_t was_running = adc_running;

  if (resolution_bits == 10U)
  {
    resolution = ADC_RESOLUTION_10B;
  }
  else if (resolution_bits == 12U)
  {
    resolution = ADC_RESOLUTION_12B;
  }
  else
  {
    return;
  }

  if (was_running != 0U)
  {
    StopAdcAcquisition();
  }

  hadc1.Init.Resolution = resolution;
  hadc2.Init.Resolution = resolution;

  if (HAL_ADC_Init(&hadc1) != HAL_OK)
  {
    Error_Handler();
  }

  if (HAL_ADC_Init(&hadc2) != HAL_OK)
  {
    Error_Handler();
  }

  multimode.Mode = ADC_DUALMODE_REGSIMULT;
  multimode.DMAAccessMode = ADC_DMAACCESSMODE_12_10_BITS;
  multimode.TwoSamplingDelay = ADC_TWOSAMPLINGDELAY_1CYCLE;
  if (HAL_ADCEx_MultiModeConfigChannel(&hadc1, &multimode) != HAL_OK)
  {
    Error_Handler();
  }

  sConfig.Channel = ADC_CHANNEL_15;
  sConfig.Rank = ADC_REGULAR_RANK_1;
  sConfig.SamplingTime = ADC_SAMPLETIME_2CYCLES_5;
  sConfig.SingleDiff = ADC_SINGLE_ENDED;
  sConfig.OffsetNumber = ADC_OFFSET_NONE;
  sConfig.Offset = 0;
  sConfig.OffsetSign = ADC_OFFSET_SIGN_NEGATIVE;
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }

  sConfig.Channel = ADC_CHANNEL_4;
  if (HAL_ADC_ConfigChannel(&hadc2, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }

  if (was_running != 0U)
  {
    StartAdcAcquisition();
  }
}

static uint8_t IsCompleteUsbCommand(const char *command)
{
  if ((strcmp(command, "BOARD?") == 0) ||
      (strcmp(command, "STATUS?") == 0) ||
      (strcmp(command, "START") == 0) ||
      (strcmp(command, "START ADC") == 0) ||
      (strcmp(command, "STOP") == 0) ||
      (strcmp(command, "STOP ADC") == 0) ||
      (strcmp(command, "DAC START") == 0) ||
      (strcmp(command, "DDS START") == 0) ||
      (strcmp(command, "DAC STOP") == 0) ||
      (strcmp(command, "DDS STOP") == 0) ||
      (strcmp(command, "MODE,PE") == 0) ||
      (strcmp(command, "MODE,PR") == 0) ||
      (strcmp(command, "PCB,PE") == 0) ||
      (strcmp(command, "PCB,PR") == 0) ||
      (strcmp(command, "ACTUATOR,DDS") == 0) ||
      (strcmp(command, "ACTUATOR,FG") == 0) ||
      (strcmp(command, "ACTUATOR,FUNCTION_GENERATOR") == 0) ||
      (strcmp(command, "ACTUATOR,STM32") == 0) ||
      (strcmp(command, "ACTUATOR,STM32_DAC") == 0))
  {
    return 1U;
  }

  if ((strncmp(command, "BUF,", 4) == 0) ||
      (strncmp(command, "ADC SAMP,", 9) == 0) ||
      (strncmp(command, "ADC RES,", 8) == 0) ||
      (strncmp(command, "DAC FREQ,", 9) == 0) ||
      (strncmp(command, "DDS FREQ,", 9) == 0) ||
      (strncmp(command, "PE GAIN,", 8) == 0))
  {
    return 1U;
  }

  return 0U;
}

static void ProcessUsbCommand(const char *command)
{
  if (strcmp(command, "BOARD?") == 0)
  {
    uint8_t stream_was_enabled = adc_stream_enabled;

    adc_stream_enabled = 0U;
    CDC_SendText("BOARD,Nucleo H7S3L8\r\n");
    adc_stream_enabled = stream_was_enabled;
  }
  else if (strcmp(command, "STATUS?") == 0)
  {
    char response[96];
    uint8_t stream_was_enabled = adc_stream_enabled;

    adc_stream_enabled = 0U;
    (void)snprintf(response,
                   sizeof(response),
                   "STATUS,B%u,A%u,G%u,DDS,%lu,%u\r\n",
                   (unsigned int)board_mode,
                   (unsigned int)actuator_mode,
                   (unsigned int)pe_gain_index,
                   (unsigned long)dds_frequency_hz,
                   (unsigned int)dds_running);
    CDC_SendText(response);
    adc_stream_enabled = stream_was_enabled;
  }
  else if ((strcmp(command, "START") == 0) || (strcmp(command, "START ADC") == 0))
  {
    adc_stream_enabled = 1U;
    if (adc_running == 0U)
    {
      StartAdcAcquisition();
    }
  }
  else if ((strcmp(command, "STOP") == 0) || (strcmp(command, "STOP ADC") == 0))
  {
    adc_stream_enabled = 0U;
    if (adc_running != 0U)
    {
      StopAdcAcquisition();
    }
  }
  else if (strncmp(command, "BUF,", 4) == 0)
  {
    uint32_t requested_size = (uint32_t)strtoul(&command[4], NULL, 10);

    SetAdcBufferSize(requested_size);
  }
  else if (strncmp(command, "ADC SAMP,", 9) == 0)
  {
    uint32_t sample_rate_hz = (uint32_t)strtoul(&command[9], NULL, 10);

    SetAdcSamplingRate(sample_rate_hz);
  }
  else if (strncmp(command, "ADC RES,", 8) == 0)
  {
    uint32_t resolution_bits = (uint32_t)strtoul(&command[8], NULL, 10);

    SetAdcResolution(resolution_bits);
  }
  else if ((strcmp(command, "DAC START") == 0) || (strcmp(command, "DDS START") == 0))
  {
    DdsStart();
  }
  else if ((strcmp(command, "DAC STOP") == 0) || (strcmp(command, "DDS STOP") == 0))
  {
    DdsStop();
  }
  else if (strncmp(command, "DAC FREQ,", 9) == 0)
  {
    DdsSetFrequency((float)strtod(&command[9], NULL));
  }
  else if (strncmp(command, "DDS FREQ,", 9) == 0)
  {
    DdsSetFrequency((float)strtod(&command[9], NULL));
  }
  else if ((strcmp(command, "MODE,PE") == 0) || (strcmp(command, "PCB,PE") == 0))
  {
    SetBoardMode(BOARD_MODE_PE);
  }
  else if ((strcmp(command, "MODE,PR") == 0) || (strcmp(command, "PCB,PR") == 0))
  {
    SetBoardMode(BOARD_MODE_PR);
  }
  else if (strcmp(command, "ACTUATOR,DDS") == 0)
  {
    SetActuatorMode(ACTUATOR_MODE_DDS);
  }
  else if ((strcmp(command, "ACTUATOR,FG") == 0) ||
           (strcmp(command, "ACTUATOR,FUNCTION_GENERATOR") == 0))
  {
    SetActuatorMode(ACTUATOR_MODE_FUNCTION_GENERATOR);
  }
  else if ((strcmp(command, "ACTUATOR,STM32") == 0) ||
           (strcmp(command, "ACTUATOR,STM32_DAC") == 0))
  {
    SetActuatorMode(ACTUATOR_MODE_STM32_DAC);
  }
  else if (strncmp(command, "PE GAIN,", 8) == 0)
  {
    SetPeGain((uint8_t)strtoul(&command[8], NULL, 10));
  }
}

void App_CDC_Receive(uint8_t *data, uint32_t length)
{
  uint8_t command_processed = 0U;

  for (uint32_t i = 0U; i < length; i++)
  {
    char c = (char)data[i];

    if ((c == '\r') || (c == '\n'))
    {
      if (usb_command_length > 0U)
      {
        usb_command_buffer[usb_command_length] = '\0';
        ProcessUsbCommand(usb_command_buffer);
        usb_command_length = 0U;
        command_processed = 1U;
      }
    }
    else if (usb_command_length < (sizeof(usb_command_buffer) - 1U))
    {
      usb_command_buffer[usb_command_length++] = c;
    }
    else
    {
      usb_command_length = 0U;
    }
  }

  if ((command_processed == 0U) && (usb_command_length > 0U))
  {
    usb_command_buffer[usb_command_length] = '\0';
    if (IsCompleteUsbCommand(usb_command_buffer) != 0U)
    {
      ProcessUsbCommand(usb_command_buffer);
      usb_command_length = 0U;
    }
  }
}

void HAL_ADC_ConvHalfCpltCallback(ADC_HandleTypeDef* hadc)
{
    if(hadc->Instance == ADC1)
    {
        // for(uint32_t i=0;i<active_buffer_size/2;i+=CHUNK_SIZE)
        // {
            // send_adc_data(&adc_buffer[i],CHUNK_SIZE);
            dma_half_complete = 1;
        // }
        // half_ready = 1;
    }
}

void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef* hadc)
{
    if(hadc->Instance == ADC1)
    {
        // for(uint32_t i=active_buffer_size/2;i<active_buffer_size;i+=CHUNK_SIZE)
        // {
            // send_adc_data(&adc_buffer[i],CHUNK_SIZE);
            dma_full_complete = 1;
        // }
        // full_ready = 1;
    }
}
/* USER CODE END 4 */

 /* MPU Configuration */

static void MPU_Config(void)
{
  MPU_Region_InitTypeDef MPU_InitStruct = {0};

  /* Disables the MPU */
  HAL_MPU_Disable();

  /* Disables all MPU regions */
  for(uint8_t i=0; i<__MPU_REGIONCOUNT; i++)
  {
    HAL_MPU_DisableRegion(i);
  }

  /** Initializes and configures the Region and the memory to be protected
  */
  MPU_InitStruct.Enable = MPU_REGION_ENABLE;
  MPU_InitStruct.Number = MPU_REGION_NUMBER0;
  MPU_InitStruct.BaseAddress = 0x24040000;
  MPU_InitStruct.Size = MPU_REGION_SIZE_128KB;
  MPU_InitStruct.SubRegionDisable = 0x0;
  MPU_InitStruct.TypeExtField = MPU_TEX_LEVEL1;
  MPU_InitStruct.AccessPermission = MPU_REGION_FULL_ACCESS;
  MPU_InitStruct.DisableExec = MPU_INSTRUCTION_ACCESS_DISABLE;
  MPU_InitStruct.IsShareable = MPU_ACCESS_SHAREABLE;
  MPU_InitStruct.IsCacheable = MPU_ACCESS_NOT_CACHEABLE;
  MPU_InitStruct.IsBufferable = MPU_ACCESS_NOT_BUFFERABLE;

  HAL_MPU_ConfigRegion(&MPU_InitStruct);
  /* Enables the MPU */
  HAL_MPU_Enable(MPU_PRIVILEGED_DEFAULT);

}

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
