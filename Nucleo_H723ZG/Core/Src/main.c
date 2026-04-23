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
#include "lwip.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "stm32h7xx_hal.h"
#include "lwip/udp.h"
#include "lwip/pbuf.h"
#include "stm32h7xx_hal_adc.h"
// #include "stm32h7xx_hal_dac.h"
#include "string.h"
#include <stdint.h>
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
#ifdef __GNUC__
#define PUTCHAR_PROTOTYPE int __io_putchar(int ch)
#else
#define PUTCHAR_PROTOTYPE int fputc(int ch, FILE *f)
#endif
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
ADC_HandleTypeDef hadc1;
ADC_HandleTypeDef hadc2;
DMA_HandleTypeDef hdma_adc1;

SPI_HandleTypeDef hspi1;

TIM_HandleTypeDef htim6;

UART_HandleTypeDef huart3;

/* USER CODE BEGIN PV */
#define Max_ADC_BUFFER_SIZE 4096 // 128kB buffer, can hold 16384 samples of 2 ADCs (32 bits each)  
__attribute__((section(".RAM_D1"), aligned(32)))
uint32_t adc_buffer[Max_ADC_BUFFER_SIZE];
volatile uint32_t active_buffer_size = Max_ADC_BUFFER_SIZE;
volatile uint8_t adc_running = 1;
// volatile uint8_t dac_running = 1;

// volatile uint8_t half_ready = 0;
// volatile uint8_t full_ready = 0;q

// uint32_t last_send_time = 0;
#define CHUNK_SIZE 256 // number of samples to send in one UDP packet (must be <= active_buffer_size/2)
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
void PeriphCommonClock_Config(void);
static void MPU_Config(void);
static void MX_GPIO_Init(void);
static void MX_DMA_Init(void);
static void MX_ADC2_Init(void);
static void MX_TIM6_Init(void);
static void MX_USART3_UART_Init(void);
static void MX_ADC1_Init(void);
static void MX_SPI1_Init(void);
/* USER CODE BEGIN PFP */
void send_adc_data(uint32_t* data, uint32_t length);
/* USER CODE BEGIN PFP */
void udp_receive_callback(void *arg,
                          struct udp_pcb *pcb,
                          struct pbuf *p,
                          const ip_addr_t *addr,
                          u16_t port);

void parse_command(char *cmd);
void update_adc_buffer_size(uint32_t new_size);
void stop_adc_acquisition(void);
void start_adc_acquisition(void);
// void process_half_buffer(void);
// void process_full_buffer(void);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */
struct udp_pcb *upcb;
struct udp_pcb *rx_pcb;
ip_addr_t dest_ip;

// #define SINE_SAMPLES 128
// uint16_t sine_table[SINE_SAMPLES];

// void generate_sine_table(void)
// {
//     for(int i = 0; i < SINE_SAMPLES; i++)
//     {
//         float angle = 2.0f * 3.14159265f * i / SINE_SAMPLES;
//         sine_table[i] = (uint16_t)(2048 + 2047 * sinf(angle));
//     }
// }
int __io_putchar(int ch)
{
  /* Place your implementation of fputc here */
  /* e.g. write a character to the USART3 and Loop until the end of transmission */
  HAL_UART_Transmit(&huart3, (uint8_t *)&ch, 1, 10);
  return ch;
}
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

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* Configure the peripherals common clocks */
  PeriphCommonClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_DMA_Init();
  MX_ADC2_Init();
  MX_TIM6_Init();
  MX_LWIP_Init();
  MX_USART3_UART_Init();
  MX_ADC1_Init();
  MX_SPI1_Init();
  /* USER CODE BEGIN 2 */
  // generate_sine_table();
  // HAL_DAC_Start_DMA(&hdac1,
  //                 DAC_CHANNEL_1,
  //                 (uint32_t*)sine_table,
  //                 SINE_SAMPLES,
  //                 DAC_ALIGN_12B_R);

  HAL_ADC_Start(&hadc2);   // start slave ADC first
  HAL_ADCEx_MultiModeStart_DMA(
      &hadc1,
      (uint32_t*)adc_buffer,
      active_buffer_size
  ); // start master ADC with DMA, this will also trigger the slave ADC conversions

  HAL_TIM_Base_Start(&htim6); // start timer, this will trigger the ADC conversions via the timer TRGO

  // Initialize UDP connection
  
  upcb = udp_new();
  IP4_ADDR(&dest_ip, 192,168,0,100);   // your PC IP
  if(upcb != NULL)
  {
      udp_connect(upcb, &dest_ip, 5005);
  }
  else
  {
      Error_Handler();
  }
  rx_pcb = udp_new();
  if(rx_pcb != NULL)
  {
      udp_bind(rx_pcb, IP_ADDR_ANY, 5006);
      udp_recv(rx_pcb, udp_receive_callback, NULL);
  }
  else
  {
      Error_Handler();
  }
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
    // 1. Handle LwIP tasks (e.g., incoming UDP packets)
    MX_LWIP_Process();
    // if (half_ready)
    
 
          // process_half_buffer();
          // process_full_buffer();
  
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Supply configuration update enable
  */
  HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY);

  /** Configure the main internal regulator output voltage
  */
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE0);

  while(!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)) {}

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLM = 1;
  RCC_OscInitStruct.PLL.PLLN = 68;
  RCC_OscInitStruct.PLL.PLLP = 1;
  RCC_OscInitStruct.PLL.PLLQ = 4;
  RCC_OscInitStruct.PLL.PLLR = 2;
  RCC_OscInitStruct.PLL.PLLRGE = RCC_PLL1VCIRANGE_3;
  RCC_OscInitStruct.PLL.PLLVCOSEL = RCC_PLL1VCOWIDE;
  RCC_OscInitStruct.PLL.PLLFRACN = 6144;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2
                              |RCC_CLOCKTYPE_D3PCLK1|RCC_CLOCKTYPE_D1PCLK1;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.SYSCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB3CLKDivider = RCC_APB3_DIV2;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_APB1_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_APB2_DIV2;
  RCC_ClkInitStruct.APB4CLKDivider = RCC_APB4_DIV2;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_3) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief Peripherals Common Clock Configuration
  * @retval None
  */
void PeriphCommonClock_Config(void)
{
  RCC_PeriphCLKInitTypeDef PeriphClkInitStruct = {0};

  /** Initializes the peripherals clock
  */
  PeriphClkInitStruct.PeriphClockSelection = RCC_PERIPHCLK_ADC;
  PeriphClkInitStruct.PLL2.PLL2M = 1;
  PeriphClkInitStruct.PLL2.PLL2N = 24;
  PeriphClkInitStruct.PLL2.PLL2P = 2;
  PeriphClkInitStruct.PLL2.PLL2Q = 2;
  PeriphClkInitStruct.PLL2.PLL2R = 2;
  PeriphClkInitStruct.PLL2.PLL2RGE = RCC_PLL2VCIRANGE_3;
  PeriphClkInitStruct.PLL2.PLL2VCOSEL = RCC_PLL2VCOWIDE;
  PeriphClkInitStruct.PLL2.PLL2FRACN = 0;
  PeriphClkInitStruct.AdcClockSelection = RCC_ADCCLKSOURCE_PLL2;
  if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInitStruct) != HAL_OK)
  {
    Error_Handler();
  }
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
  hadc1.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV1;
  hadc1.Init.Resolution = ADC_RESOLUTION_16B;
  hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
  hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
  hadc1.Init.LowPowerAutoWait = DISABLE;
  hadc1.Init.ContinuousConvMode = DISABLE;
  hadc1.Init.NbrOfConversion = 1;
  hadc1.Init.DiscontinuousConvMode = DISABLE;
  hadc1.Init.ExternalTrigConv = ADC_EXTERNALTRIG_T6_TRGO;
  hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_RISING;
  hadc1.Init.ConversionDataManagement = ADC_CONVERSIONDATA_DMA_CIRCULAR;
  hadc1.Init.Overrun = ADC_OVR_DATA_PRESERVED;
  hadc1.Init.LeftBitShift = ADC_LEFTBITSHIFT_NONE;
  hadc1.Init.OversamplingMode = DISABLE;
  hadc1.Init.Oversampling.Ratio = 1;
  if (HAL_ADC_Init(&hadc1) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure the ADC multi-mode
  */
  multimode.Mode = ADC_DUALMODE_REGSIMULT;
  multimode.DualModeData = ADC_DUALMODEDATAFORMAT_32_10_BITS;
  multimode.TwoSamplingDelay = ADC_TWOSAMPLINGDELAY_1CYCLE;
  if (HAL_ADCEx_MultiModeConfigChannel(&hadc1, &multimode) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Regular Channel
  */
  sConfig.Channel = ADC_CHANNEL_15;
  sConfig.Rank = ADC_REGULAR_RANK_1;
  sConfig.SamplingTime = ADC_SAMPLETIME_8CYCLES_5;
  sConfig.SingleDiff = ADC_SINGLE_ENDED;
  sConfig.OffsetNumber = ADC_OFFSET_NONE;
  sConfig.Offset = 0;
  sConfig.OffsetSignedSaturation = DISABLE;
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
  hadc2.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV1;
  hadc2.Init.Resolution = ADC_RESOLUTION_16B;
  hadc2.Init.ScanConvMode = ADC_SCAN_DISABLE;
  hadc2.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
  hadc2.Init.LowPowerAutoWait = DISABLE;
  hadc2.Init.ContinuousConvMode = DISABLE;
  hadc2.Init.NbrOfConversion = 1;
  hadc2.Init.DiscontinuousConvMode = DISABLE;
  hadc2.Init.ConversionDataManagement = ADC_CONVERSIONDATA_DR;
  hadc2.Init.Overrun = ADC_OVR_DATA_PRESERVED;
  hadc2.Init.LeftBitShift = ADC_LEFTBITSHIFT_NONE;
  hadc2.Init.OversamplingMode = DISABLE;
  hadc2.Init.Oversampling.Ratio = 1;
  if (HAL_ADC_Init(&hadc2) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Regular Channel
  */
  sConfig.Channel = ADC_CHANNEL_5;
  sConfig.Rank = ADC_REGULAR_RANK_1;
  sConfig.SamplingTime = ADC_SAMPLETIME_8CYCLES_5;
  sConfig.SingleDiff = ADC_SINGLE_ENDED;
  sConfig.OffsetNumber = ADC_OFFSET_NONE;
  sConfig.Offset = 0;
  sConfig.OffsetSignedSaturation = DISABLE;
  if (HAL_ADC_ConfigChannel(&hadc2, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN ADC2_Init 2 */

  /* USER CODE END ADC2_Init 2 */

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
  hspi1.Init.CRCPolynomial = 0x0;
  hspi1.Init.NSSPMode = SPI_NSS_PULSE_ENABLE;
  hspi1.Init.NSSPolarity = SPI_NSS_POLARITY_LOW;
  hspi1.Init.FifoThreshold = SPI_FIFO_THRESHOLD_01DATA;
  hspi1.Init.TxCRCInitializationPattern = SPI_CRC_INITIALIZATION_ALL_ZERO_PATTERN;
  hspi1.Init.RxCRCInitializationPattern = SPI_CRC_INITIALIZATION_ALL_ZERO_PATTERN;
  hspi1.Init.MasterSSIdleness = SPI_MASTER_SS_IDLENESS_00CYCLE;
  hspi1.Init.MasterInterDataIdleness = SPI_MASTER_INTERDATA_IDLENESS_00CYCLE;
  hspi1.Init.MasterReceiverAutoSusp = SPI_MASTER_RX_AUTOSUSP_DISABLE;
  hspi1.Init.MasterKeepIOState = SPI_MASTER_KEEP_IO_STATE_DISABLE;
  hspi1.Init.IOSwap = SPI_IO_SWAP_DISABLE;
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
  htim6.Init.Prescaler = 0;
  htim6.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim6.Init.Period = 109;
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
  * @brief USART3 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART3_UART_Init(void)
{

  /* USER CODE BEGIN USART3_Init 0 */

  /* USER CODE END USART3_Init 0 */

  /* USER CODE BEGIN USART3_Init 1 */

  /* USER CODE END USART3_Init 1 */
  huart3.Instance = USART3;
  huart3.Init.BaudRate = 115200;
  huart3.Init.WordLength = UART_WORDLENGTH_8B;
  huart3.Init.StopBits = UART_STOPBITS_1;
  huart3.Init.Parity = UART_PARITY_NONE;
  huart3.Init.Mode = UART_MODE_TX_RX;
  huart3.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart3.Init.OverSampling = UART_OVERSAMPLING_16;
  huart3.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
  huart3.Init.ClockPrescaler = UART_PRESCALER_DIV1;
  huart3.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
  if (HAL_UART_Init(&huart3) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_UARTEx_SetTxFifoThreshold(&huart3, UART_TXFIFO_THRESHOLD_1_8) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_UARTEx_SetRxFifoThreshold(&huart3, UART_RXFIFO_THRESHOLD_1_8) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_UARTEx_DisableFifoMode(&huart3) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART3_Init 2 */

  /* USER CODE END USART3_Init 2 */

}

/**
  * Enable DMA controller clock
  */
static void MX_DMA_Init(void)
{

  /* DMA controller clock enable */
  __HAL_RCC_DMA1_CLK_ENABLE();

  /* DMA interrupt init */
  /* DMA1_Stream0_IRQn interrupt configuration */
  HAL_NVIC_SetPriority(DMA1_Stream0_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(DMA1_Stream0_IRQn);

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
  __HAL_RCC_GPIOH_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOE_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();
  __HAL_RCC_GPIOG_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOE, GPIO_PIN_7|GPIO_PIN_8|GPIO_PIN_9|GPIO_PIN_11
                          |GPIO_PIN_13, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOE, GPIO_PIN_14, GPIO_PIN_SET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOD, GPIO_PIN_14, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOG, GPIO_PIN_14, GPIO_PIN_RESET);

  /*Configure GPIO pins : PE7 PE8 PE9 PE11
                           PE13 PE14 */
  GPIO_InitStruct.Pin = GPIO_PIN_7|GPIO_PIN_8|GPIO_PIN_9|GPIO_PIN_11
                          |GPIO_PIN_13|GPIO_PIN_14;
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

  /*Configure GPIO pin : PG14 */
  GPIO_InitStruct.Pin = GPIO_PIN_14;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOG, &GPIO_InitStruct);

  /* USER CODE BEGIN MX_GPIO_Init_2 */

  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */
void stop_adc_acquisition(void)
{
    HAL_TIM_Base_Stop(&htim6);
    HAL_ADCEx_MultiModeStop_DMA(&hadc1);
    HAL_ADC_Stop(&hadc2);
    adc_running = 0;
}

void start_adc_acquisition(void)
{
    HAL_Delay(1);  // Add a small delay
    HAL_ADC_Start(&hadc2);   // restart slave ADC
    HAL_ADCEx_MultiModeStart_DMA(
        &hadc1,
        (uint32_t*)adc_buffer,
        active_buffer_size
    );
    HAL_TIM_Base_Start(&htim6);
    adc_running = 1;
}
void update_buffer_size(uint32_t new_size)
{
    if(new_size < 512 || new_size > Max_ADC_BUFFER_SIZE)
        return;

    if(adc_running == 1)
    {
      
        stop_adc_acquisition();
    }
    active_buffer_size = new_size;
}
void update_adc_sampling_rate(uint32_t fs)
{
    if(fs < 1000 || fs > 2500000)
        return;

    uint32_t pclk = HAL_RCC_GetPCLK1Freq();
    uint32_t timer_clk = ((RCC->D2CFGR & RCC_D2CFGR_D2PPRE1) != 0) ? (pclk * 2) : pclk;

    uint32_t period = (timer_clk / fs) - 1;
    if(period > 0xFFFF)
        return;

    uint8_t was_running = adc_running;

    if(was_running)
        stop_adc_acquisition();

    __HAL_TIM_SET_AUTORELOAD(&htim6, period);
    __HAL_TIM_SET_COUNTER(&htim6, 0);
    // if(was_running)
    //     start_adc_acquisition();
}
void update_adc_resolution(uint32_t bits)
{
    if(bits != 10 && bits != 12 && bits != 14 && bits != 16)
        return;

    uint32_t res;
    switch(bits)
    {
        case 10: res = ADC_RESOLUTION_10B; break;
        case 12: res = ADC_RESOLUTION_12B; break;
        case 14: res = ADC_RESOLUTION_14B; break;
        case 16: res = ADC_RESOLUTION_16B; break;
        default: return;
    }

    uint8_t was_running = adc_running;

    if(was_running)
        stop_adc_acquisition();

    HAL_ADC_DeInit(&hadc1);
    HAL_ADC_DeInit(&hadc2);

    hadc1.Init.Resolution = res;
    hadc2.Init.Resolution = res;

    if (HAL_ADC_Init(&hadc1) != HAL_OK)
        Error_Handler();

    if (HAL_ADC_Init(&hadc2) != HAL_OK)
        Error_Handler();

    ADC_MultiModeTypeDef multimode = {0};
    multimode.Mode = ADC_DUALMODE_REGSIMULT;
    multimode.DualModeData = ADC_DUALMODEDATAFORMAT_32_10_BITS;
    multimode.TwoSamplingDelay = ADC_TWOSAMPLINGDELAY_1CYCLE;

    if (HAL_ADCEx_MultiModeConfigChannel(&hadc1, &multimode) != HAL_OK)
        Error_Handler();

    ADC_ChannelConfTypeDef sConfig = {0};

    sConfig.Channel = ADC_CHANNEL_15;
    sConfig.Rank = ADC_REGULAR_RANK_1;
    sConfig.SamplingTime = ADC_SAMPLETIME_8CYCLES_5;
    sConfig.SingleDiff = ADC_SINGLE_ENDED;
    sConfig.OffsetNumber = ADC_OFFSET_NONE;
    sConfig.Offset = 0;
    sConfig.OffsetSignedSaturation = DISABLE;

    if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
        Error_Handler();

    sConfig.Channel = ADC_CHANNEL_5;
    sConfig.Rank = ADC_REGULAR_RANK_1;
    sConfig.SamplingTime = ADC_SAMPLETIME_1CYCLE_5;
    sConfig.SingleDiff = ADC_SINGLE_ENDED;
    sConfig.OffsetNumber = ADC_OFFSET_NONE;
    sConfig.Offset = 0;
    sConfig.OffsetSignedSaturation = DISABLE;

    if (HAL_ADC_ConfigChannel(&hadc2, &sConfig) != HAL_OK)
        Error_Handler();

    /* keep stopped until Start ADC is pressed */
}
void udp_receive_callback(void *arg,
                          struct udp_pcb *pcb,
                          struct pbuf *p,
                          const ip_addr_t *addr,
                          u16_t port)
{
    if(p != NULL)
    {
        char buffer[64];

        uint16_t len = (p->len < 63) ? p->len : 63;
        memcpy(buffer,p->payload,len);
        buffer[len] = '\0';

        parse_command(buffer);

        pbuf_free(p);
    }
}
void parse_command(char *cmd)
{
    if(strncmp(cmd,"BUF",3)==0)
    {
        uint32_t size;

        sscanf(cmd,"BUF,%lu",&size);

        update_buffer_size(size);
    }
    else if(strncmp(cmd,"ADC SAMP",8)==0)
    {
        uint32_t fs;

        sscanf(cmd,"ADC SAMP,%lu",&fs);

        update_adc_sampling_rate(fs);
    }
    else if(strncmp(cmd,"START",5)==0)
    {
        if(adc_running == 0)
          {
            start_adc_acquisition();
          }
    }
    else if(strncmp(cmd,"STOP",4)==0)
    {
        if(adc_running == 1)
          {
            stop_adc_acquisition();
            
          }
    }
    else if (strncmp(cmd, "ADC RES", 7) == 0)
    {
        uint32_t bits;
        sscanf(cmd, "ADC RES,%lu", &bits);
        update_adc_resolution(bits);
    }
}
void send_adc_data(uint32_t* data, uint32_t length)
{
    // struct pbuf *p;

    // p = pbuf_alloc(PBUF_TRANSPORT, length * sizeof(uint32_t), PBUF_RAM);
    // if(p != NULL && upcb != NULL)
    // {
    //     memcpy(p->payload, data, length * sizeof(uint32_t));
    //     udp_send(upcb, p);
    //     pbuf_free(p);
    // }
 // To avoid the overhead of copying data into the pbuf, we can use PBUF_REF and point it directly to our ADC buffer. This is more efficient but requires that we ensure the data remains valid until the pbuf is sent.
    struct pbuf *p;
    p = pbuf_alloc(PBUF_TRANSPORT, 0, PBUF_REF);
    if(p != NULL && upcb != NULL)
    {
        p->payload = (void*)data;
        p->len = length * sizeof(uint32_t);
        p->tot_len = p->len;
        // VERY IMPORTANT: clean DCache
        SCB_CleanDCache_by_Addr((uint32_t*)data, p->len);
        udp_send(upcb, p);

        pbuf_free(p);
    }
}
/* Triggered when the first half of DMA buffer is ready */
void HAL_ADC_ConvHalfCpltCallback(ADC_HandleTypeDef* hadc)
{
    if (hadc->Instance == ADC1)
    {
        for (uint32_t i = 0; i < active_buffer_size / 2; i += CHUNK_SIZE)
        {
            SCB_CleanDCache_by_Addr((uint32_t *)&adc_buffer[i], CHUNK_SIZE * sizeof(uint32_t));

            struct pbuf *p = pbuf_alloc(PBUF_TRANSPORT, CHUNK_SIZE * sizeof(uint32_t), PBUF_REF);
            if (p != NULL)
            {
                p->payload = (void *)&adc_buffer[i];
                p->len     = CHUNK_SIZE * sizeof(uint32_t);
                p->tot_len = p->len;

                udp_send(upcb, p);
                pbuf_free(p);
            }
        }
    }
}

/* Triggered when the second half of DMA buffer is ready */
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef* hadc)
{
    if (hadc->Instance == ADC1)
    {
        for (uint32_t i = active_buffer_size / 2; i < active_buffer_size; i += CHUNK_SIZE)
        {
            SCB_CleanDCache_by_Addr((uint32_t *)&adc_buffer[i], CHUNK_SIZE * sizeof(uint32_t));

            struct pbuf *p = pbuf_alloc(PBUF_TRANSPORT, CHUNK_SIZE * sizeof(uint32_t), PBUF_REF);
            if (p != NULL)
            {
                p->payload = (void *)&adc_buffer[i];
                p->len     = CHUNK_SIZE * sizeof(uint32_t);
                p->tot_len = p->len;

                udp_send(upcb, p);
                pbuf_free(p);
            }
        }
    }
}


/* USER CODE END 4 */

 /* MPU Configuration */

void MPU_Config(void)
{
  MPU_Region_InitTypeDef MPU_InitStruct = {0};

  /* Disables the MPU */
  HAL_MPU_Disable();

  /** Initializes and configures the Region and the memory to be protected
  */
  MPU_InitStruct.Enable = MPU_REGION_ENABLE;
  MPU_InitStruct.Number = MPU_REGION_NUMBER0;
  MPU_InitStruct.BaseAddress = 0x30000000;
  MPU_InitStruct.Size = MPU_REGION_SIZE_32KB;
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
