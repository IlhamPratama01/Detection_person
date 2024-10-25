"use client";
import "../globals.css";
import { useState, useEffect, useRef } from "react";
import axios from "axios";
import Hls from "hls.js";

export function Video() {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedVideoRef, setSelectedVideoRef] = useState("videoRef1"); // State to switch between refs
  const videoRef1 = useRef(null);
  const videoRef2 = useRef(null);

  // Video options
  const videoOptions = [
    { value: "videoRef1", label: "Video Heatmaps " },
    { value: "videoRef2", label: "Video Anotasi " },
  ];

  // Function to handle file selection
  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
  };

  // Function to submit the file to the backend
  const handleSubmit = async () => {
    if (!file) {
      alert("Please upload a file first!");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setIsUploading(true);

    try {
      const response = await axios.post(
        "http://localhost:8000/process_video/",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      if (response.status === 200) {
        // Process successful upload here if needed
      } else {
        alert("Error: Unable to upload video.");
      }
    } catch (error) {
      console.error("There was an error uploading the video!", error);
      alert("There was an error uploading the video!");
    } finally {
      setIsUploading(false);
    }
  };

  // Function to load video source based on selected reference
  const loadVideo = (ref) => {
    const video = ref.current;
    const videoSource =
      ref === videoRef1
        ? "http://localhost:8000/heatsmap/mapsoutput.m3u8"
        : "http://localhost:8000/hls_output/output.m3u8"; // Adjust URLs as needed

    if (Hls.isSupported()) {
      const hls = new Hls();
      hls.loadSource(videoSource);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play();
      });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = videoSource;
      video.addEventListener("loadedmetadata", () => {
        video.play();
      });
    }
  };

  useEffect(() => {
    // Load video source when selectedVideoRef changes
    const selectedRef =
      selectedVideoRef === "videoRef1" ? videoRef1 : videoRef2;
    loadVideo(selectedRef);
  }, [selectedVideoRef]);

  return (
    <div
      className="bg-white border border-gray-200 rounded-xl p-2 sm:p-6 mx-auto w-auto xl:w-[902px] h-auto xl:h-[630px]"
      style={{ boxShadow: "5px 7px 2px rgba(0, 0, 0, 0.6)" }}
    >
      <div className="text-center">
        <h5 className="text-2xl mb-2 font-bold tracking-tight text-gray-900">
          Human Detections
        </h5>
        <div className="flex flex-col items-center justify-center relative z-10">
          {/* Video Element */}
          {selectedVideoRef === "videoRef1" ? (
            <video
              ref={videoRef1}
              className="w-full h-96 border-2 aspect-video rounded-lg mb-4 object-contain"
              autoPlay
              controls
              loop
              style={{ boxShadow: "5px 7px 2px rgba(0, 0, 0, 0.2)" }}
            />
          ) : (
            <video
              ref={videoRef2}
              className="w-full h-96 border-2 aspect-video rounded-lg mb-4 object-contain"
              autoPlay
              controls
              loop
              style={{ boxShadow: "5px 7px 2px rgba(0, 0, 0, 0.2)" }}
            />
          )}
        </div>
      </div>
      <div className="mt-4">
        <select
          id="videoSelect"
          value={selectedVideoRef}
          onChange={(e) => setSelectedVideoRef(e.target.value)}
          className="block w-34 mb-2 text-xs text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50"
        >
          {videoOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <label
          className="block mb-2 text-sm font-bold text-gray-900"
          htmlFor="file_input"
        >
          Upload File
        </label>
        <input
          className="block w-full mb-2 text-xs text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50"
          id="file_input"
          type="file"
          accept="video/*"
          onChange={handleFileChange}
        />
        <button
          type="button"
          className="w-full text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 me-2 mb-2"
          style={{ boxShadow: "5px 7px 2px rgba(0, 0, 255, 0.3)" }}
          onClick={handleSubmit}
        >
          {isUploading ? "Processing..." : "Submit"}
        </button>
      </div>
    </div>
  );
}
