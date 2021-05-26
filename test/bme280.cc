// 検算用プログラム
// 変換部分のソースは https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme280-ds002.pdf より
// 標準入力に p t h のセンサの読み値を入れると、
// 標準出力に以下を出力する(入力と出力で順序が違うので注意)
//   整数補正後の t_fine
//   整数補正後の t p h
//   整数補正後を単位変換した t p h
//   double補正後の t_fine
//   double 補正後の t p h
//
// コンパイルは、以下で行う(Makefileを用意したので、makeでも良い)
// c++ -o bme280 bme280.cc

#include <iostream>

typedef int BME280_S32_t;
typedef unsigned int BME280_U32_t;
typedef long long int BME280_S64_t;

// 以下は calibration data。必要に応じて BME280 からの読み値に変更する。
int dig_T1 = 28998;
int dig_T2 = 27158;
int dig_T3 = 50;
int dig_P1 = 36231;
int dig_P2 = -10432;
int dig_P3 = 3024;
int dig_P4 = 7042;
int dig_P5 = -68;
int dig_P6 = -7;
int dig_P7 = 9900;
int dig_P8 = -10230;
int dig_P9 = 4285;
int dig_H1 = 75;
int dig_H2 = 378;
int dig_H3 = 0;
int dig_H4 = 282;
int dig_H5 = 50;
int dig_H6 = 30;

// 以下は、p.25 4.2.3Compensation formulas のコード

// Returns temperature in DegC, resolution is 0.01 DegC. Output value of “5123” equals 51.23 DegC.
// t_fine carries fine temperature as global value
BME280_S32_t t_fine = (BME280_S32_t)0;
BME280_S32_t BME280_compensate_T_int32(BME280_S32_t adc_T)
{
    BME280_S32_t var1, var2, T;
    var1 = ((((adc_T >> 3) - ((BME280_S32_t)dig_T1 << 1))) * ((BME280_S32_t)dig_T2)) >> 11;
    var2 = (((((adc_T >> 4) - ((BME280_S32_t)dig_T1)) * ((adc_T >> 4) - ((BME280_S32_t)dig_T1))) >> 12) *
            ((BME280_S32_t)dig_T3)) >>
           14;
    t_fine = var1 + var2;
    T = (t_fine * 5 + 128) >> 8;
    return T;
}

// Returns pressure in Pa as unsigned 32 bit integer in Q24.8 format (24 integer bits and 8 fractional bits).
// Output value of “24674867” represents 24674867/256 = 96386.2 Pa = 963.862 hPa
BME280_U32_t BME280_compensate_P_int64(BME280_S32_t adc_P)
{
    BME280_S64_t var1, var2, p;
    var1 = ((BME280_S64_t)t_fine) - 128000;
    var2 = var1 * var1 * (BME280_S64_t)dig_P6;
    var2 = var2 + ((var1 * (BME280_S64_t)dig_P5) << 17);
    var2 = var2 + (((BME280_S64_t)dig_P4) << 35);
    var1 = ((var1 * var1 * (BME280_S64_t)dig_P3) >> 8) + ((var1 * (BME280_S64_t)dig_P2) << 12);
    var1 = (((((BME280_S64_t)1) << 47) + var1)) * ((BME280_S64_t)dig_P1) >> 33;
    if (var1 == 0)
    {
        return 0; // avoid exception caused by division by zero
    }
    p = 1048576 - adc_P;
    p = (((p << 31) - var2) * 3125) / var1;
    var1 = (((BME280_S64_t)dig_P9) * (p >> 13) * (p >> 13)) >> 25;
    var2 = (((BME280_S64_t)dig_P8) * p) >> 19;
    p = ((p + var1 + var2) >> 8) + (((BME280_S64_t)dig_P7) << 4);
    return (BME280_U32_t)p;
}

// Returns humidity in %RH as unsigned 32 bit integer in Q22.10 format (22 integer and 10 fractional bits).
// Output value of “47445” represents 47445/1024 = 46.333 %RH
BME280_U32_t bme280_compensate_H_int32(BME280_S32_t adc_H)
{
    BME280_S32_t v_x1_u32r;
    v_x1_u32r = (t_fine - ((BME280_S32_t)76800));
    v_x1_u32r = (((((adc_H << 14) - (((BME280_S32_t)dig_H4) << 20) - (((BME280_S32_t)dig_H5) * v_x1_u32r)) + ((BME280_S32_t)16384)) >> 15) * (((((((v_x1_u32r * ((BME280_S32_t)dig_H6)) >> 10) * (((v_x1_u32r * ((BME280_S32_t)dig_H3)) >> 11) + ((BME280_S32_t)32768))) >> 10) + ((BME280_S32_t)2097152)) * ((BME280_S32_t)dig_H2) + 8192) >> 14));
    v_x1_u32r = (v_x1_u32r - (((((v_x1_u32r >> 15) * (v_x1_u32r >> 15)) >> 7) * ((BME280_S32_t)dig_H1)) >> 4));
    v_x1_u32r = (v_x1_u32r < 0 ? 0 : v_x1_u32r);
    v_x1_u32r = (v_x1_u32r > 419430400 ? 419430400 : v_x1_u32r);
    return (BME280_U32_t)(v_x1_u32r >> 12);
}

// 以下は、p.49 8.1Compensation formulas in  double precision floating point のコード

// Returns temperature in DegC, double precision. Output value of “51.23” equals 51.23 DegC.
// t_fine carries fine temperature as global value
//BME280_S32_t t_fine;
double BME280_compensate_T_double(BME280_S32_t adc_T)
{
    double var1, var2, T;
    var1 = (((double)adc_T) / 16384.0 - ((double)dig_T1) / 1024.0) * ((double)dig_T2);
    var2 = ((((double)adc_T) / 131072.0 - ((double)dig_T1) / 8192.0) * (((double)adc_T) / 131072.0 - ((double)dig_T1) / 8192.0)) * ((double)dig_T3);
    t_fine = (BME280_S32_t)(var1 + var2);
    T = (var1 + var2) / 5120.0;
    return T;
}

// Returns pressure in Pa as double. Output value of “96386.2” equals 96386.2 Pa = 963.862 hPa
double BME280_compensate_P_double(BME280_S32_t adc_P)
{
    double var1, var2, p;
    var1 = ((double)t_fine / 2.0) - 64000.0;
    var2 = var1 * var1 * ((double)dig_P6) / 32768.0;
    var2 = var2 + var1 * ((double)dig_P5) * 2.0;
    var2 = (var2 / 4.0) + (((double)dig_P4) * 65536.0);
    var1 = (((double)dig_P3) * var1 * var1 / 524288.0 + ((double)dig_P2) * var1) / 524288.0;
    var1 = (1.0 + var1 / 32768.0) * ((double)dig_P1);
    if (var1 == 0.0)
    {
        return 0;
        // avoid exception caused by division by zero
    }
    p = 1048576.0 - (double)adc_P;
    p = (p - (var2 / 4096.0)) * 6250.0 / var1;
    var1 = ((double)dig_P9) * p * p / 2147483648.0;
    var2 = p * ((double)dig_P8) / 32768.0;
    p = p + (var1 + var2 + ((double)dig_P7)) / 16.0;
    return p;
}

// Returns humidity in %rH as as double. Output value of “46.332” represents 46.332 %rH
double bme280_compensate_H_double(BME280_S32_t adc_H)
{
    double var_H;
    var_H = (((double)t_fine) - 76800.0);
    var_H = (adc_H - (((double)dig_H4) * 64.0 + ((double)dig_H5) / 16384.0 * var_H)) * (((double)dig_H2) / 65536.0 * (1.0 + ((double)dig_H6) / 67108864.0 * var_H * (1.0 + ((double)dig_H3) / 67108864.0 * var_H)));
    var_H = var_H * (1.0 - ((double)dig_H1) * var_H / 524288.0);
    if (var_H > 100.0)
        var_H = 100.0;
    else if (var_H < 0.0)
        var_H = 0.0;
    return var_H;
}

int main()
{
    BME280_S32_t raw_t, raw_p, raw_h;
    std::cin >> raw_p >> raw_t >> raw_h;
    int t = BME280_compensate_T_int32((BME280_S32_t)raw_t);
    int p = BME280_compensate_P_int64((BME280_S32_t)raw_p);
    int h = bme280_compensate_H_int32((BME280_S32_t)raw_h);
    std::cout << t_fine << std::endl;
    std::cout << t << " " << p << " " << h << std::endl;
    std::cout << (t / 100.) << " " << (p / 256.) << " " << (h / 1024.) << std::endl;
    double dt = BME280_compensate_T_double(raw_t);
    double dp = BME280_compensate_P_double(raw_p);
    double dh = bme280_compensate_H_double(raw_h);
    std::cout << t_fine << std::endl;
    std::cout << dt << " " << dp << " " << dh << std::endl;
    return 0;
}
