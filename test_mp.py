import mediapipe as mp
print("MediaPipe version:", getattr(mp, "__version__", "unknown"))
print("Available attributes in mediapipe:")
print([attr for attr in dir(mp) if not attr.startswith("_")])

try:
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    print("\nMediaPipe Tasks API is AVAILABLE!")
except Exception as e:
    print("\nTasks API error:", e)

try:
    from mediapipe.python import solutions
    print("Legacy Solutions API is AVAILABLE!")
except Exception as e:
    print("Legacy Solutions error:", e)
