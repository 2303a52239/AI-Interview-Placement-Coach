import { useCallback, useEffect, useRef, useState } from "react";
import { transcribeAudio, getErrorMessage } from "../services/api";

/**
 * Voice input with two strategies:
 *  1. Browser Web Speech API (Chrome/Edge) - live transcript, no server needed.
 *  2. Fallback for other browsers: record with MediaRecorder, then send the audio
 *     to POST /speech/transcribe (works only if the backend has OPENAI_API_KEY).
 *
 * onText(text) is called with the full transcript so far.
 * onError(message) is called with a user-friendly message.
 */
export function useVoiceInput({ onText, onError }) {
  const SpeechRecognition =
    typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);
  const canRecordAudio =
    typeof window !== "undefined" && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== "undefined";

  const supported = !!SpeechRecognition || canRecordAudio;
  const mode = SpeechRecognition ? "browser" : canRecordAudio ? "server" : "none";

  const [listening, setListening] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const recognitionRef = useRef(null);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const onTextRef = useRef(onText);
  const onErrorRef = useRef(onError);
  onTextRef.current = onText;
  onErrorRef.current = onError;

  useEffect(() => () => {
    recognitionRef.current?.abort?.();
    recorderRef.current?.stream?.getTracks().forEach((t) => t.stop());
  }, []);

  const start = useCallback(async () => {
    if (mode === "browser") {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = "en-US";
      recognition.onresult = (event) => {
        let transcript = "";
        for (let i = 0; i < event.results.length; i++) transcript += event.results[i][0].transcript;
        onTextRef.current?.(transcript);
      };
      recognition.onerror = (e) => {
        setListening(false);
        const msg = e.error === "not-allowed"
          ? "Microphone access was blocked. Allow it in your browser's address bar and try again."
          : e.error === "no-speech" ? "No speech was detected. Try again." : "Voice input stopped unexpectedly.";
        onErrorRef.current?.(msg);
      };
      recognition.onend = () => setListening(false);
      recognitionRef.current = recognition;
      recognition.start();
      setListening(true);
      return;
    }

    if (mode === "server") {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const recorder = new MediaRecorder(stream);
        chunksRef.current = [];
        recorder.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
        recorder.onstop = async () => {
          stream.getTracks().forEach((t) => t.stop());
          const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
          setTranscribing(true);
          try {
            const res = await transcribeAudio(blob);
            onTextRef.current?.(res.data.text);
          } catch (err) {
            onErrorRef.current?.(getErrorMessage(err, "Could not transcribe the recording. Please type your answer."));
          } finally {
            setTranscribing(false);
          }
        };
        recorderRef.current = recorder;
        recorder.start();
        setListening(true);
      } catch {
        onErrorRef.current?.("Could not access the microphone. Check browser permissions.");
      }
    }
  }, [mode, SpeechRecognition]);

  const stop = useCallback(() => {
    if (mode === "browser") recognitionRef.current?.stop();
    if (mode === "server" && recorderRef.current?.state === "recording") recorderRef.current.stop();
    setListening(false);
  }, [mode]);

  return { supported, mode, listening, transcribing, start, stop };
}
