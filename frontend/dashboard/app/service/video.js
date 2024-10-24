"use client";
import "../globals.css";
import { useState, useEffect, useRef } from "react";
import axios from "axios";
import Hls from "hls.js";

export function Video() {
  const [file, setFile] = useState(null);
  const [videoUrl, setVideoUrl] = useState("");
  const [isUploading, setIsUploading] = useState(false); // State for upload status
  const videoRef = useRef(null);
  const videoRef2 = useRef(null); // Ref for video element

  // Fetch video URL from localStorage on component mount
  useEffect(() => {
    const savedVideoUrl = localStorage.getItem("videoUrl");
    if (savedVideoUrl) {
      setVideoUrl(savedVideoUrl); // Set video URL from localStorage if exists
    }
  }, []);

  // Function to handle file selection
  const handleFileChange = (event) => {
    setFile(event.target.files[0]); // Set selected file
  };

  // Function to submit the file to the backend
  const handleSubmit = async () => {
    if (!file) {
      alert("Please upload a file first!");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setIsUploading(true); // Set uploading status

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
        const videoSource = response.data.video_url;
        setVideoUrl(videoSource); // Set video URL from server response
        localStorage.setItem("videoUrl", videoSource); // Store video URL in localStorage
      } else {
        alert("Error: Unable to upload video.");
      }
    } catch (error) {
      console.error("There was an error uploading the video!", error);
      alert("There was an error uploading the video!");
    } finally {
      setIsUploading(false); // Reset uploading status
    }
  };

useEffect(() => {
  if (videoUrl && videoRef.current) {
    const video = videoRef.current;
    let hls;

    if (Hls.isSupported()) {
      hls = new Hls({
        debug: true,
        enableWorker: true,
        lowLatencyMode: true,
        manifestLoadingTimeOut: 10000,
        manifestLoadingMaxRetry: 5,
        manifestLoadingRetryDelay: 1000,
        levelLoadingTimeOut: 10000,
        levelLoadingMaxRetry: 5,
        levelLoadingRetryDelay: 1000,
        fragLoadingTimeOut: 20000,
        fragLoadingMaxRetry: 5,
        fragLoadingRetryDelay: 1000,
      });

      hls.loadSource("http://localhost:8000/heatsmap/mapsoutput.m3u8"); // Update source here
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        console.log("Manifest parsed, starting playback");
        video.play();
      });

      hls.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              console.log("Fatal network error encountered, trying to recover");
              hls.startLoad();
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              console.log("Fatal media error encountered, trying to recover");
              hls.recoverMediaError();
              break;
            default:
              console.log("Fatal error, cannot recover");
              hls.destroy();
              break;
          }
        }
      });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = "http://localhost:8000/heatsmap/output.m3u8";
      video.addEventListener("loadedmetadata", () => {
        video.play();
      });
    }

    return () => {
      if (hls) {
        hls.destroy();
      }
    };
  }
}, [videoUrl]);
  // Function to handle HLS video loading
  // useEffect(() => {
  //   if (videoUrl && videoRef.current) {
  //     const video = videoRef.current;
  //     let hls;

  //     if (Hls.isSupported()) {
  //       hls = new Hls({
  //         debug: true,
  //         enableWorker: true,
  //         lowLatencyMode: true,
  //         manifestLoadingTimeOut: 10000,
  //         manifestLoadingMaxRetry: 5,
  //         manifestLoadingRetryDelay: 1000,
  //         levelLoadingTimeOut: 10000,
  //         levelLoadingMaxRetry: 5,
  //         levelLoadingRetryDelay: 1000,
  //         fragLoadingTimeOut: 20000,
  //         fragLoadingMaxRetry: 5,
  //         fragLoadingRetryDelay: 1000,
  //       });

  //       hls.loadSource("http://localhost:8000/hls_output/output.m3u8"); // Update source here
  //       hls.attachMedia(video);
  //       hls.on(Hls.Events.MANIFEST_PARSED, () => {
  //         console.log("Manifest parsed, starting playback");
  //         video.play();
  //       });

  //       hls.on(Hls.Events.ERROR, (event, data) => {
  //         if (data.fatal) {
  //           switch (data.type) {
  //             case Hls.ErrorTypes.NETWORK_ERROR:
  //               console.log("Fatal network error encountered, trying to recover");
  //               hls.startLoad();
  //               break;
  //             case Hls.ErrorTypes.MEDIA_ERROR:
  //               console.log("Fatal media error encountered, trying to recover");
  //               hls.recoverMediaError();
  //               break;
  //             default:
  //               console.log("Fatal error, cannot recover");
  //               hls.destroy();
  //               break;
  //           }
  //         }
  //       });
  //     } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
  //       video.src = "http://localhost:8000/hls_output/output.m3u8";
  //       video.addEventListener("loadedmetadata", () => {
  //         video.play();
  //       });
  //     }

  //     return () => {
  //       if (hls) {
  //         hls.destroy();
  //       }
  //     };
  //   }
  // }, [videoUrl]); // Reload HLS when videoUrl changes

  return (
    <div
      className="bg-white border border-gray-200 rounded-xl p-2 sm:p-6 mx-auto w-auto xl:w-[902px] h-auto xl:h-[590px]"
      style={{
        boxShadow: "5px 7px 2px rgba(0, 0, 0, 0.6)", // Shadow on right and bottom
      }}
    >
      <div className="text-center">
        <h5 className="text-2xl mb-2 font-bold tracking-tight text-gray-900">
          Human Detections
        </h5>
        <div className="flex flex-col md:flex-row space-y-5 md:space-y-0 md:space-x-2 items-center justify-center relative z-10">
        {/* <video
          ref={videoRef} // Use ref for video element
          className="w-80 h-96 border-2 aspect-video rounded-lg object-contain"
          autoPlay
          controls
          loop
          style={{ boxShadow: "5px 7px 2px rgba(0, 0, 0, 0.2)" }}
        /> */}
        <video
          ref={videoRef} // Use ref for video element
          className="w-full h-96 border-2 aspect-video rounded-lg object-contain"
          autoPlay
          controls
          loop
          style={{ boxShadow: "5px 7px 2px rgba(0, 0, 0, 0.2)" }}
        />
        </div>
      </div>
      <div className="mt-6">
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
          accept="video/*" // Only accept video files
          onChange={handleFileChange} // Handle file change
        />
        <button
          type="button"
          className="w-full text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 me-2 mb-2"
          style={{ boxShadow: "5px 7px 2px rgba(0, 0, 255, 0.3)" }}
          onClick={handleSubmit} // Submit file on button click
        >
          {isUploading ? (
            <div className="flex items-center justify-center">
              <svg
                className="animate-spin h-5 w-5 mr-3 text-white"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  fill="currentColor"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 1 1 16 0 8 8 0 0 1-16 0zm4-1h8a4 4 0 1 0-8 0z"
                />
              </svg>
              Processing...
            </div>
          ) : (
            "Submit"
          )}
        </button>
      </div>
    </div>
  );
}
