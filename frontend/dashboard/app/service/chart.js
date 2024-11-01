"use client";
import "../globals.css";
import React, { useEffect, useState, useRef } from "react";
import ApexCharts from "apexcharts";

export function Chart() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const chartRef = useRef(null);
  const [average, setAverage] = useState(0);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch("/api/person");
        if (!response.ok) throw new Error("Network response was not ok");

        const result = await response.json();
        const personCounts = result.map((row) => ({
          person_count: row.person_count,
          // Tambahkan atribut lain yang diperlukan
        }));

        const averagePersonCount = Math.max(
          ...personCounts.map((row) => row.person_count)
        );

        setAverage(averagePersonCount);
        const limitedData = result
          .filter((row) => row.person_count >= 1)
          .slice(-5)
          .sort((a, b) => b.person_count - a.person_count); // Filter untuk mendapatkan hanya entri dengan person_count >= 40

        const personData = limitedData.map((row) => row.person_count);
        const headData = limitedData.map((row) => row.head_count);
        const categories = limitedData.map((row) => {
          const date = new Date(row.created_at);
          return date.toLocaleDateString("id-ID", { weekday: "long" }); // Mengambil nama hari dalam Bahasa Indonesia
        }); // Assuming created_at is the category

        setData({
          categories,
          series: [
            { name: "Human Data", data: personData, color: "#1A56DB" },
            { name: "Head Data", data: headData, color: "#FDBA8C" },
          ],
        });
      } catch (error) {
        setError(error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  useEffect(() => {
    if (data) {
      const options = {
        colors: ["#1A56DB", "#FDBA8C"],
        series: data.series,
        chart: {
          type: "bar",
          height: "320px",
          fontFamily: "Inter, sans-serif",
          toolbar: {
            show: false,
          },
        },
        plotOptions: {
          bar: {
            horizontal: false,
            columnWidth: "70%",
            borderRadiusApplication: "end",
            borderRadius: 8,
          },
        },
        tooltip: {
          shared: true,
          intersect: false,
          style: {
            fontFamily: "Inter, sans-serif",
          },
        },
        states: {
          hover: {
            filter: {
              type: "darken",
              value: 1,
            },
          },
        },
        stroke: {
          show: true,
          width: 0,
          colors: ["transparent"],
        },
        grid: {
          show: false,
          strokeDashArray: 4,
          padding: {
            left: 2,
            right: 2,
            top: -14,
          },
        },
        dataLabels: {
          enabled: false,
        },
        legend: {
          show: false,
        },
        xaxis: {
          categories: data.categories,
          labels: {
            show: true,
            style: {
              fontFamily: "Inter, sans-serif",
              cssClass: "text-xs font-normal fill-gray-500 dark:fill-gray-400",
            },
          },
          axisBorder: {
            show: false,
          },
          axisTicks: {
            show: false,
          },
        },
        yaxis: {
          show: true, // Set to true to show the y-axis
        },
        fill: {
          opacity: 1,
        },
      };

      if (chartRef.current) {
        const chart = new ApexCharts(chartRef.current, options);
        chart.render();
        return () => {
          chart.destroy();
        };
      }
    }
  }, [data]);

  if (loading) return <p>Loading...</p>;
  if (error) return <p>Error: {error.message}</p>;

  return (
    <div
      className="border w-auto h-auto sm:w-[600px] sm:h-[595px] bg-white rounded-lg shadow dark:bg-gray-800 p-4 md:p-6"
      style={{
        boxShadow: "5px 7px 2px rgba(0, 0, 0, 0.2)",
      }}
    >
      <div className="flex justify-between pb-4 mb-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center">
          <div className="w-12 h-12 rounded-lg bg-gray-100 dark:bg-gray-700 flex items-center justify-center me-3">
            <svg
              className="w-6 h-6 text-gray-500 dark:text-gray-400"
              aria-hidden="true"
              xmlns="http://www.w3.org/2000/svg"
              fill="currentColor"
              viewBox="0 0 20 19"
            >
              <path d="M14.5 0A3.987 3.987 0 0 0 11 2.1a4.977 4.977 0 0 1 3.9 5.858A3.989 3.989 0 0 0 14.5 0ZM9 13h2a4 4 0 0 1 4 4v2H5v-2a4 4 0 0 1 4-4Z" />
              <path d="M5 19h10v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2ZM5 7a5.008 5.008 0 0 1 4-4.9 3.988 3.988 0 1 0-3.9 5.859A4.974 4.974 0 0 1 5 7Zm5 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm5-1h-.424a5.016 5.016 0 0 1-1.942 2.232A6.007 6.007 0 0 1 17 17h2a1 1 0 0 0 1-1v-2a5.006 5.006 0 0 0-5-5ZM5.424 9H5a5.006 5.006 0 0 0-5 5v2a1 1 0 0 0 1 1h2a6.007 6.007 0 0 1 4.366-5.768A5.016 5.016 0 0 1 5.424 9Z" />
            </svg>
          </div>
          <div>
            <h5 className="leading-none text-2xl font-bold text-gray-900 dark:text-white pb-1">
              {average} Person
            </h5>
            <p className="text-sm font-normal text-gray-500 dark:text-gray-400">
            Peak Occupancy
            </p>
          </div>
        </div>
        <div>
          <span className="bg-green-100 text-green-800 text-xs font-medium inline-flex items-center px-2.5 py-1 rounded-md dark:bg-green-900 dark:text-green-300">
            <svg
              className="w-2.5 h-2.5 me-1.5"
              aria-hidden="true"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 10 14"
            >
              <path
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M5 13V1m0 0L1 5m4-4 4 4"
              />
            </svg>
            42.5%
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2">
      </div>
      <div
        ref={chartRef}
        id="column-chart"
        className="w-full h-[200px] sm:h-[300px]"
      />
    </div>
  );
}

export function Pie() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [average, setAverage] = useState(0);
  const chartRef = useRef(null);
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch("/api/person");
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }

        const result = await response.json();
        const personCounts = result.map((row) => row.person_count);
        const averagePersonCount =
          personCounts.reduce((sum, count) => sum + count, 0) /
          personCounts.length;

        setAverage(averagePersonCount);

        const headAndPersonData = result.map((item) => ({
          head_count: item.head_count, // Ambil 'head_count'
          person_count: item.person_count, // Ambil 'person_count'
        }));

        const sortedByHead = [...headAndPersonData].sort(
          (a, b) => b.head_count - a.head_count
        );
        const sortedByPerson = [...headAndPersonData].sort(
          (a, b) => b.person_count - a.person_count
        );

        const highestPerson = sortedByPerson[0].person_count;
        const highestHead = sortedByHead[0].head_count;

        setData({ highestPerson, highestHead });
      } catch (err) {
        console.error("Error fetching data:", err);
        setError(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  useEffect(() => {
    if (!data || loading) return;
    const getChartOptions = () => {
      return {
        series: [data.highestPerson, data.highestHead],
        colors: ["#1C64F2", "#16BDCA"],
        chart: {
          height: 320,
          width: "100%",
          type: "donut",
        },
        stroke: {
          colors: ["transparent"],
        },
        plotOptions: {
          pie: {
            donut: {
              labels: {
                show: true,
                name: {
                  show: true,
                  fontFamily: "Inter, sans-serif",
                  offsetY: 20,
                },
                total: {
                  showAlways: true,
                  show: true,
                  label: "Human Detections",
                  fontFamily: "Inter, sans-serif",
                  formatter: (w) => {
                    const sum = w.globals.seriesTotals.reduce(
                      (a, b) => a + b,
                      0
                    );
                    return "Total " + sum + "";
                  },
                },
                value: {
                  show: true,
                  fontFamily: "Inter, sans-serif",
                  offsetY: -20,
                  formatter: (value) => value + "k",
                },
              },
              size: "80%",
            },
          },
        },
        grid: {
          padding: {
            top: -2,
          },
        },
        labels: ["Person", "Head"],
        dataLabels: {
          enabled: false,
        },
        legend: {
          position: "bottom",
          fontFamily: "Inter, sans-serif",
        },
        yaxis: {
          labels: {
            formatter: (value) => value + "",
          },
        },
        xaxis: {
          labels: {
            formatter: (value) => value + "",
          },
          axisTicks: {
            show: false,
          },
          axisBorder: {
            show: false,
          },
        },
      };
    };

    // Cek jika chartRef.current sudah terikat ke elemen DOM
    if (chartRef.current) {
      // Render chart baru
      const chart = new ApexCharts(chartRef.current, getChartOptions());
      chart.render();

      // Clean up dengan cara destroy chart saat komponen unmount atau saat data berubah
      return () => {
        console.log("Destroying chart...");
        chart.destroy();
      };
    }
  }, [data, loading]);

  return (
    <div
      className="border w-auto h-auto sm:w-[600px] sm:h-[595px] bg-white rounded-lg shadow dark:bg-gray-800 p-4 md:p-6"
      style={{
        boxShadow: "5px 7px 2px rgba(0, 0, 0, 0.2)",
      }}
    >
      <div className="flex justify-between mb-3">
        <div className="flex justify-center items-center">
          <h5 className="text-xl font-bold leading-none text-gray-900 dark:text-white pe-1">
            Human traffic
          </h5>
          <svg
            data-popover-target="chart-info"
            data-popover-placement="bottom"
            className="w-3.5 h-3.5 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white cursor-pointer ms-1"
            aria-hidden="true"
            xmlns="http://www.w3.org/2000/svg"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path d="M10 .5a9.5 9.5 0 1 0 9.5 9.5A9.51 9.51 0 0 0 10 .5Zm0 16a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Zm1-5.034V12a1 1 0 0 1-2 0v-1.418a1 1 0 0 1 1.038-.999 1.436 1.436 0 0 0 1.488-1.441 1.501 1.501 0 1 0-3-.116.986.986 0 0 1-1.037.961 1 1 0 0 1-.96-1.037A3.5 3.5 0 1 1 11 11.466Z" />
          </svg>
          <div
            data-popover
            id="chart-info"
            role="tooltip"
            className="absolute z-10 invisible inline-block text-sm text-gray-500 transition-opacity duration-300 bg-white border border-gray-200 rounded-lg shadow-sm opacity-0 w-72 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-400"
          >
            <div data-popper-arrow></div>
          </div>
        </div>
        <div>
          <button
            type="button"
            data-tooltip-target="data-tooltip"
            data-tooltip-placement="bottom"
            className="hidden sm:inline-flex items-center justify-center text-gray-500 w-8 h-8 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-4 focus:ring-gray-200 dark:focus:ring-gray-700 rounded-lg text-sm"
          >
            <svg
              className="w-3.5 h-3.5"
              aria-hidden="true"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 16 18"
            >
              <path
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M8 1v11m0 0 4-4m-4 4L4 8m11 4v3a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2v-3"
              />
            </svg>
            <span className="sr-only">Download data</span>
          </button>
        </div>
      </div>

      <div></div>

      {/* Donut Chart */}
      <div ref={chartRef} className="py-6" id="donut-chart"></div>

      <div className="grid grid-cols-1 items-center border-gray-200 border-t dark:border-gray-700 justify-between">
        <div className="flex justify-between items-center pt-5">
          {/* Button */}
          <button
            id="dropdownDefaultButton"
            data-dropdown-toggle="lastDaysdropdown"
            data-dropdown-placement="bottom"
            className="text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-900 text-center inline-flex items-center dark:hover:text-white"
            type="button"
          >
            Last 7 days
            <svg
              className="w-2.5 m-2.5 ms-1.5"
              aria-hidden="true"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 10 6"
            >
              <path
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="m1 1 4 4 4-4"
              />
            </svg>
          </button>

          {/* Dropdown */}
        </div>

        <div className="flex justify-between pt-5 pb-4">
          <div className="flex flex-col">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Today
            </span>
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {average.toFixed(2)}
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Last week
            </span>
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {average.toFixed(2)}
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Last month
            </span>
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {average.toFixed(2)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function Line() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const chartRef = useRef(null);
  const [average, setAverage] = useState(0);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch("/api/person");
        if (!response.ok) throw new Error("Network response was not ok");

        const result = await response.json();

        const limitedData = result.slice(0, 20);
        const personCounts = result.map((row) => row.person_count);
        const averagePersonCount =
          personCounts.reduce((sum, count) => sum + count, 0) /
          personCounts.length;

        setAverage(averagePersonCount);
        // Map and format data for chart categories and series
        const categories = limitedData.map((row) => {
          const date = new Date(row.created_at);
          return date.toLocaleTimeString([], {
            hour: "2-digit",
            hour12: false,
            minute: "2-digit",
          });
        });
        const personData = limitedData.map((row) => row.person_count);
        const headData = limitedData.map((row) => row.head_count);

        setData({
          categories,
          series: [
            { name: "Human Data", data: personData, color: "#1A56DB" },
            { name: "Head Data", data: headData, color: "#7E3BF2" },
          ],
        });
      } catch (error) {
        setError(error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  useEffect(() => {
    if (data) {
      const options = {
        xaxis: {
          show: true,
          categories: data.categories,
          labels: {
            show: true,
            style: {
              fontFamily: "Inter, sans-serif",
              cssClass: "text-xs font-normal fill-gray-500 dark:fill-gray-400",
            },
          },
          axisBorder: { show: false },
          axisTicks: { show: false },
        },
        yaxis: {
          show: true,
          min: 0, // Set batas bawah ke 0
          max: 50,
          labels: {
            show: true,
            style: {
              fontFamily: "Inter, sans-serif",
              cssClass: "text-xs font-normal fill-gray-500 dark:fill-gray-400",
            },
            formatter: (value) => "" + value,
          },
        },
        series: data.series,
        chart: {
          sparkline: { enabled: false },
          height: "100%",
          width: "100%",
          type: "area",
          fontFamily: "Inter, sans-serif",
          dropShadow: { enabled: false },
          toolbar: { show: false },
        },
        tooltip: {
          enabled: true,
          x: { show: false },
        },
        fill: {
          type: "gradient",
          gradient: {
            opacityFrom: 0.55,
            opacityTo: 0,
            shade: "#1C64F2",
            gradientToColors: ["#1C64F2"],
          },
        },
        dataLabels: { enabled: false },
        stroke: { width: 6 },
        legend: { show: false },
        grid: { show: false },
      };

      const chart = new ApexCharts(chartRef.current, options);
      chart.render();

      return () => chart.destroy();
    }
  }, [data]);

  if (loading) return <p>Loading...</p>;
  if (error) return <p>Error: {error.message}</p>;

  return (
    <div
      className="border w-full bg-white rounded-lg shadow dark:bg-gray-800 xl:w-[1224px]"
      style={{ boxShadow: "5px 7px 2px rgba(0, 0, 0, 0.2)" }}
    >
      <div className="flex justify-between p-4 md:p-6 pb-0 md:pb-0">
        <div className="flex items-center">
          <div className="w-12 h-12 rounded-lg bg-gray-100 dark:bg-gray-700 flex items-center justify-center me-3">
            <svg
              className="w-6 h-6 text-gray-500 dark:text-gray-400"
              aria-hidden="true"
              xmlns="http://www.w3.org/2000/svg"
              fill="currentColor"
              viewBox="0 0 20 19"
            >
              <path d="M14.5 0A3.987 3.987 0 0 0 11 2.1a4.977 4.977 0 0 1 3.9 5.858A3.989 3.989 0 0 0 14.5 0ZM9 13h2a4 4 0 0 1 4 4v2H5v-2a4 4 0 0 1 4-4Z" />
              <path d="M5 19h10v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2ZM5 7a5.008 5.008 0 0 1 4-4.9 3.988 3.988 0 1 0-3.9 5.859A4.974 4.974 0 0 1 5 7Zm5 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm5-1h-.424a5.016 5.016 0 0 1-1.942 2.232A6.007 6.007 0 0 1 17 17h2a1 1 0 0 0 1-1v-2a5.006 5.006 0 0 0-5-5ZM5.424 9H5a5.006 5.006 0 0 0-5 5v2a1 1 0 0 0 1 1h2a6.007 6.007 0 0 1 4.366-5.768A5.016 5.016 0 0 1 5.424 9Z" />
            </svg>
          </div>
          <div>
            <h5 className="leading-none text-2xl font-bold text-gray-900 dark:text-white pb-1">
              {average.toFixed(0)} Person
            </h5>
            <p className="text-sm font-normal text-gray-500 dark:text-gray-400">
              Average this week
            </p>
          </div>
        </div>
      </div>
      <div id="labels-chart" ref={chartRef} className="px-2.5"></div>
    </div>
  );
}
