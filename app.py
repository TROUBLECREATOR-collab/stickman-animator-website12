from flask import Flask, render_template, request, send_file, jsonify
import os
import uuid
import cv2
import numpy as np

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/generated_videos'

# Create upload folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

class StickmanAnimator:
    def __init__(self, canvas_size=(600, 600)):
        self.canvas_size = canvas_size
        self.joint_connections = [
            (0, 1), (1, 2), (2, 3),  # Right arm
            (1, 4), (4, 5), (5, 6),  # Left arm
            (1, 7), (7, 8), (8, 9),  # Right leg
            (1, 10), (10, 11), (11, 12)  # Left leg
        ]
        self.pose_library = self._create_pose_library()
    
    def _create_pose_library(self):
        return {
            "neutral": [
                (300, 100), (300, 200), (250, 150), (200, 150),
                (350, 150), (400, 150), (250, 350), (250, 500),
                (350, 350), (350, 500), (300, 200), (300, 200), (300, 200)
            ],
            "punch_right": [
                (300, 100), (300, 200), (280, 180), (250, 200),
                (350, 150), (400, 150), (250, 350), (250, 500),
                (350, 350), (350, 500), (300, 200), (300, 200), (300, 200)
            ],
            "punch_left": [
                (300, 100), (300, 200), (250, 150), (200, 150),
                (320, 180), (350, 200), (250, 350), (250, 500),
                (350, 350), (350, 500), (300, 200), (300, 200), (300, 200)
            ],
            "kick_right": [
                (300, 100), (300, 200), (250, 150), (200, 150),
                (350, 150), (400, 150), (280, 300), (320, 400),
                (350, 350), (350, 500), (300, 200), (300, 200), (300, 200)
            ],
            "victory": [
                (300, 100), (300, 200), (250, 100), (200, 80),
                (350, 100), (400, 80), (250, 350), (250, 500),
                (350, 350), (350, 500), (300, 200), (300, 200), (300, 200)
            ]
        }
    
    def interpolate_poses(self, pose1, pose2, steps):
        frames = []
        for step in range(steps):
            t = step / (steps - 1) if steps > 1 else 0
            ease_t = t * t * (3 - 2 * t)
            frame_pose = []
            for (x1, y1), (x2, y2) in zip(pose1, pose2):
                new_x = int(x1 + (x2 - x1) * ease_t)
                new_y = int(y1 + (y2 - y1) * ease_t)
                frame_pose.append((new_x, new_y))
            frames.append(frame_pose)
        return frames
    
    def draw_stickman(self, canvas, pose, color=(0, 255, 0), thickness=3):
        for x, y in pose:
            cv2.circle(canvas, (x, y), 6, color, -1)
        
        for start_idx, end_idx in self.joint_connections:
            if start_idx < len(pose) and end_idx < len(pose):
                start_pos = pose[start_idx]
                end_pos = pose[end_idx]
                cv2.line(canvas, start_pos, end_pos, color, thickness)
        
        if len(pose) > 0:
            head_x, head_y = pose[0]
            cv2.circle(canvas, (head_x, head_y), 12, color, thickness)
        
        return canvas
    
    def create_animation(self, sequence):
        frames = []
        for i in range(len(sequence) - 1):
            start_pose = self.pose_library[sequence[i]["pose"]]
            end_pose = self.pose_library[sequence[i + 1]["pose"]]
            transition_frames = self.interpolate_poses(start_pose, end_pose, sequence[i]["frames"])
            
            for frame_pose in transition_frames:
                canvas = np.ones((*self.canvas_size, 3), dtype=np.uint8) * 255
                canvas = self.draw_stickman(canvas, frame_pose, color=(0, 100, 255), thickness=3)
                frames.append(canvas)
        return frames
    
    def save_animation(self, frames, filename, fps=15):
        if not frames:
            return False
        
        height, width = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(filename, fourcc, fps, (width, height))
        
        for frame in frames:
            out.write(frame)
        
        out.release()
        return True

class FightChoreographer:
    def interpret_prompt(self, prompt):
        prompt = prompt.lower()
        sequence = [{"pose": "neutral", "frames": 15}]
        
        if "punch" in prompt:
            if "right" in prompt:
                sequence.extend([{"pose": "punch_right", "frames": 10}])
            if "left" in prompt:
                sequence.extend([{"pose": "punch_left", "frames": 10}])
        
        if "kick" in prompt:
            sequence.extend([{"pose": "kick_right", "frames": 12}])
        
        sequence.append({"pose": "victory", "frames": 20})
        return sequence

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_animation():
    try:
        fight_description = request.form['fight_description']
        
        animator = StickmanAnimator()
        choreographer = FightChoreographer()
        
        sequence = choreographer.interpret_prompt(fight_description)
        frames = animator.create_animation(sequence)
        
        filename = f"animation_{uuid.uuid4().hex[:8]}.mp4"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        success = animator.save_animation(frames, filepath)
        
        if success:
            return jsonify({
                'success': True,
                'video_url': f'/static/generated_videos/{filename}'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to create animation'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
