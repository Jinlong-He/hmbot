test_understanding_prompt = """
## BACKGROUND
Suppose you are mobile phone app testers specialized in cross-platform testing. You are good at extracting testing scenarios from source scripts and understanding the functional intent behind them. Here is the source script to be extracted:
```python
{}
```
## YOUR TASK
Please read the source script carefully, try to understand it and ultimately answer the following questions.
1.What kind of functionality is the script designed to test?
2.Summarize the detailed test steps in the testing procedure(including `operation type`, `parameters` and `description`).
3.What is the expected result of implementation? 
Additionally, I've provided screenshots of the function tested by this script to assist you in further understanding.
Answer these three questions one by one to ensure the accuracy.

## CONSTRAINT
Your output must strictly be a valid jSON object with three keys!
`Target Function`: the answer to the first question.
`Test Steps`: the answer to the second question. Its format must be a list, where each item is a sublist containing `operation type`, `parameters` and `description`.
`Result`: the answer to the third question.
Return **only** the JSON object without any additional text, explanations, or formatting.

## EXAMPLE
Example target script: 
`d(description="确定").click()
d(resourceId="com.android.settings:id/device_name").set_text("Xiaomi 14")`
Example answers: 
```json
{{
    "Target Function": "Implement a click on the OK button.",
    "Test Steps": [
        {{
            "Operation Type": "Click",
            "Parameters": "description=\"确定\"",
            "description": "A click on the OK button."
        }},
        {{
            "Operation Type": "Input",
            "Parameters": "resourceId=\"com.android.settings:id/device_name\", text=\"Xiaomi 14\"",
            "description": "Enter 'Xiaomi 14' as the new device name."
        }},
    ],
    "Result": "Button is successfully clicked to achieve the action."
}}
```
"""


first_window_understanding_prompt = """
## Task
Based on the provided screenshot of a mobile application interface, identify which types of audio content the app likely contains or supports.

## Audio Categories to Identify
- Navigation: Voice guidance for directions and location-based instructions
- Music: Music playback, streaming services, audio players
- Video: Video players with audio, live streams, or multimedia content
- Communication: Voice/video calls

## Analysis Guidelines
Examine the interface elements to identify audio-related features:
- Look for media controls: play/pause buttons, playback sliders, volume controls
- Identify navigation elements: maps, route indicators, direction markers
- Check for video content: video thumbnails, player controls, streaming indicators
- Spot communication features: call buttons, voice message icons, contact lists, navigation bars with "Messages" tabs

## Application Type Considerations
Different app categories typically support different audio types:
- Navigation apps: ONLY include Navigation category and IGNORE all other categories
- Media apps: May include Music and/or Video features
- Social/Messaging apps: Often include Communication features (calls, voice messages)
- Other apps: May include any audio category based on visible UI elements

## Important Rules
1. For navigation apps, ONLY include Navigation category and IGNORE all other categories (Music, Video, Communication)
2. Communication features require clear indicators of voice/video calls
3. Apps with "消息" (Messages), "聊天" (Chat), or similar options in the navigation bar typically include Communication features
4. Text-only interactions (comments, forums, text chat) are NOT considered Communication audio features
5. Only select categories with clear visual evidence in the interface

## Output Format
Return ONLY a array containing the identified audio categories, chosen from:
["Navigation", "Music", "Video", "Communication"]

Example responses:
["Navigation"]
["Music", "Video"]
["Video", "Communication"]
"""

audio_off_prompt = """
## Task: Stop Currently Playing Audio

## Objective: Use the correct interface controls to completely stop any audio currently playing in the application.

## Background Context: Applications may play audio through music, video, navigation, or call features. While the exact methods to stop audio may vary, they typically follow some common interaction patterns.

## Recommended Methods to Stop Audio:
1. If currently on a music playback interface, directly click the play/pause button.
2. If currently on a video playback interface:
   - Click the play/pause button.
   - Click on any exit icon that may appear in the top-right corner.
   - Click on different main sections in the bottom navigation bar (e.g., "Home", "Messages", "Profile", "Settings").
3. If currently on a call interface, directly click the hang-up button.
4. If currently on a navigation interface, exit the navigation state.
5. If currently on another interface, click on any exit icon that may appear in the top-right corner.

## Success Confirmation:
Once the audio completely stops, the test is considered successful. Signs of success include:
   - Any visible playback controls (e.g., play/pause button) returning to their initial or "paused" state.
   - Video interface showing a pause indicator.
   - Audio player interface or overlay closing, minimizing, or disappearing.
"""



# audio_off_prompt = """
# ## Task Scenario: Audio Termination
# You are exploring how to stop currently playing audio. Your primary goal is to find and use the correct controls to stop the current audio playback.

# ## Background
# Applications may play audio through various features. The method to stop audio may vary but generally follows similar patterns.

# ## Testing Objective
# Successfully stop the currently playing audio by following these steps in order:
# 1. Try clicking tabs in the bottom navigation bar (like "Messages", "Home", or other sections) to navigate away from the current screen
#    - This is often the quickest way to exit audio playback in many applications
#    - If navigating away doesn't stop the audio, proceed with the steps below

# 2. Try pressing the back button
#    - If the back button doesn't stop the audio, proceed with the steps below

# 3. Look for and try these common controls:
#    - Pause/Stop button (typically shown as a pause or stop icon)
#    - Close or exit buttons (usually in corners or as overlay controls)
#    - Click on the playing content itself (many apps support this for pausing)

# ## Success Criteria
# The test is considered successful when the audio has stopped playing, typically indicated by:
# - Playback controls returning to initial state
# - Progress indicators stopping
# - Audio interface closing or exiting
# - No sound coming from device speaker

# Focus on ensuring that the audio has completely stopped playing. You do not need to verify other functions - simply confirming that the audio has stopped is sufficient to consider the test successfully completed.
# """

first_window_audio_prompt = """
## Task
Analyze the provided screenshot of a mobile application interface where audio is currently playing. Identify which type of audio is playing based on the visual elements and interface context.

## Audio Categories
The audio must be classified as exactly ONE of these four types:
- Navigation: Voice guidance for directions and location-based instructions
- Music: Music playback, streaming services, audio players
- Video: Video players with audio, live streams, or multimedia content
- Communication: Voice/video calls, voice messages

## Analysis Guidelines
Look for clear visual indicators that show which type of audio is currently playing:

For Navigation audio:
- Map displays with route highlighting
- Turn-by-turn instruction panels
- Distance/time remaining indicators
- Direction arrows or movement indicators

For Music audio:
- Music player interfaces with album art
- Song title, artist information
- Playback controls (play/pause, skip, etc.)
- Progress bars showing track timeline
- Playlist or queue information

For Video audio:
- Video content visible on screen
- Video player controls
- Video timeline/progress bar
- Video title or description
- Resolution or quality controls

For Communication audio:
- Call interface with contact information
- Call duration timer
- Microphone mute/unmute controls
- Speaker controls
- Contact photo or avatar
- Voice message playback interface

## Important Rules
1. Select ONLY ONE category that best matches the current playing audio
2. Focus on the most prominent audio-related interface elements
3. If multiple audio types appear possible, prioritize based on which interface elements are most active or in focus
4. Base your decision on visual evidence in the interface, not assumptions

## Output Format
Return ONLY one of these four strings, without any additional text:
navigation
music
video
communication
"""

navigation_audio_prompt = """
## Task Scenario: Navigation Audio Exploration
You are exploring applications to find and test navigation voice guidance functionality. Your primary goal is to activate voice guidance features in any application that might provide them.

## Background
Many applications provide voice guidance features, including dedicated navigation apps, map services, fitness tracking apps, and even some ride-sharing or delivery services. The core functionality involves initiating a guided journey with audio instructions.

## Testing Objective
Successfully activate voice guidance in the application. This requires completing the following steps:

1. Find a search bar or destination input field in the interface
2. If you see any history destinations, suggested locations, or popular destinations, select one directly by clicking on it
3. If no direct destination options are visible, only then enter a common destination (such as "airport", "train station", or "city center")
4. After selecting or searching for a destination, look for and click on the most relevant result
5. Look for and activate navigation or route planning features (usually a "Start", "Go", or "Navigate" button)
6. Confirm any prompts or dialogs to begin guidance
7. Ensure voice guidance is enabled in the settings (if not enabled by default)

## Success Criteria
The test is considered successful when voice guidance is activated. This is typically indicated by:
- A route displayed on a map
- The interface changing to a guidance mode
- Navigation controls becoming visible
- Active guidance running with voice instructions
- Voice prompts being played through the device speaker (such as "Turn right in 200 meters")

Focus on ensuring that the voice guidance feature is working properly, as this is the primary audio functionality being tested. You do not need to complete the entire navigation journey - simply confirming that voice guidance has been activated is sufficient.
"""

music_audio_prompt = """
## Task Scenario: Music Audio Exploration
You are exploring applications to find and test music playback functionality. Your primary goal is to activate music playback features in any application that might provide them.

## Background
Many applications provide music playback features, including dedicated music players, streaming services, video platforms with music content, social media apps, and even some games or fitness apps. The core functionality involves selecting and playing audio content.

## Testing Objective
Successfully play music in the application. This requires completing the following steps:

1. Look for and click any prominent play button on the main screen - if available, this is the quickest way to start playback
2. If no direct play button is available, navigate through the content library or collection interface
3. Look for music categories such as songs, albums, artists, playlists, or recommended content
4. Select any available music track, album, or playlist
5. Activate the play function to start audio playback
6. Verify playback status: Check if the play button has changed to a pause button and if the playback progress is moving

## Success Criteria
The test is considered successful as soon as music playback begins. This is typically indicated by:
- A track beginning to play with visible playback controls
- Play button changing to pause button (confirm the play button has been clicked and changed to pause state)
- Playback progress indicators becoming active (check if the progress bar is moving)
- Track information being displayed
- You may hear audio playing through the device speaker

Focus on ensuring that the music playback feature is working properly, as this is the primary audio functionality being tested. You do not need to evaluate the audio quality or complete playback of the entire track - simply initiating music playback is sufficient to consider the test successful. However, please ensure that playback has actually started, not just that a track has been selected but not yet playing.
"""

video_audio_prompt = """
## Task Scenario: Video Playback Exploration
You are exploring applications to find and test video playback functionality. Your primary goal is to activate video playback features in any application that might provide them, including both regular videos and live streaming content.

## Background
Many applications provide video playback features, including dedicated video players, streaming platforms, social media apps, news applications, educational apps, and even some games or fitness apps. The core functionality involves selecting and playing video content, which may include pre-recorded videos or live streams.

## Testing Objective
Successfully play a video in the application. This requires completing the following steps:
1. Look for and click any prominent video thumbnail or video play button on the main screen - if available, this is the quickest way to start playback
2. If no direct video play option is available, navigate through the video content library or collection interface
3. Look for video categories such as recent videos, popular videos, recommended videos, trending videos, featured video content, or live streams
4. Pay special attention to any "Live" or "Streaming" sections, as these contain real-time video content
5. Select any available video content (either pre-recorded or live stream) - IMPORTANT: ensure it is actual video content with visual elements, NOT audio-only or music content
6. Activate the play function to start video playback
7. Verify playback status: Check if the video is playing with visible video content on screen

## Success Criteria
The test is considered successful as soon as video playback begins. This is typically indicated by:
- Video content (recorded or live) starting to play with visible video frames on screen
- Play button changing to pause button
- Playback progress indicators becoming active (for pre-recorded videos)
- Video information being displayed
- Live indicator showing for streaming content
- Visual content clearly visible on screen

## Important Restrictions
- STRICTLY AVOID selecting or playing music-only content without visual elements
- Do NOT test audio-only features or music players
- Focus EXCLUSIVELY on content that has visual video components
- If you encounter a music player or audio-only content, continue searching for proper video content

Focus on ensuring that the video playback feature is working properly, as this is the primary functionality being tested. You do not need to evaluate the video quality or complete playback of the entire video - simply initiating video playback is sufficient to consider the test successful. Both regular video playback and live streaming are considered valid forms of video content for this test.
"""

communication_audio_prompt = """
## Task Scenario: Communication Audio Exploration
You are exploring applications to find and test communication audio functionality. Your primary goal is to activate voice or video call features in any application that might provide them.

## Background
Many applications provide communication audio features, including messaging apps, social platforms, video conferencing tools, and VoIP services. The core functionality involves initiating voice or video calls with contacts or friends.

## Testing Objective
Successfully activate voice or video call functionality in the application. Follow these steps in order:

1. Look for tabs, buttons, or sections labeled "Messages", "Contacts", "Chats" or similar social connection features
2. Navigate to the contacts or friends list section of the application
3. Select any available contact or friend from the list
4. Look for call buttons - typically represented by phone icons (for voice calls) or camera/video icons (for video calls)
   - If both voice call and video call options are available, ALWAYS prioritize and choose the voice call option
   - If there is only a combined call button, click it and then select voice call if prompted
5. Tap on the selected call button to initiate a call
6. If prompted for permissions to access microphone or camera, grant the permissions
7. Wait for the call to connect or for the calling interface to appear
8. IMPORTANT: Once the call interface appears, look for and tap the speaker or loudspeaker button to enable audio output through the device speaker

## Success Criteria
The test is considered successful when the application initiates a call. This is typically indicated by:
- Call connection screen appearing
- Ringing or connecting sound playing
- Call timer starting
- Microphone activation indicators appearing
- Call control buttons (mute, speaker, end call) becoming visible
- Speaker mode is enabled (speaker icon is highlighted or active)

Focus on initiating the call functionality - you do not need to complete an entire call session. Simply confirming that the call feature has been activated is sufficient to consider the test successful.

## Important Notes
- Prioritize finding actual contacts/friends lists rather than general messaging features
- Look specifically for direct call buttons rather than messaging or other communication options
- ALWAYS prioritize voice calls over video calls when both options are available
- Avoid any features related to video content, music playback, or live streaming - focus exclusively on person-to-person communication
- Always ensure the speaker is turned on when the call interface appears, as this is essential for audio testing
"""

other_audio_prompt = """
## Task Scenario: General Application Sound Testing
You are testing an application that doesn't clearly fall into common categories. Your primary goal is to explore the application and find any feature that produces sound through the device's speaker.

## Background
Various applications may integrate sound features in different ways, including notifications, feedback sounds, media playback, or interactive sound effects.

## Testing Objective
Systematically explore the application to find and activate any sound features. Try the following approaches in order of priority:

1. Look for and tap any obvious media controls (play buttons, sound icons, speaker symbols, etc.)
2. Browse through the main functional areas of the app, looking for sections that might contain audio content
3. Check settings menus for sound, notification, or audio-related options
4. Try completing main tasks or interactions in the app, noting if there are feedback sounds
5. If the app has search functionality, search for terms like "sound", "music", "audio", "video", etc.
6. Look for and use any tutorials, help, or example content, which often contain audio instructions

## Success Criteria
The test is considered successful when the application produces any audible sound through the device's speaker. Success indicators include:
- Any audio content playing
- Interface interaction sounds
- Notification or alert sounds
- System feedback sounds

The primary goal of exploring the application is to discover any sound functionality, regardless of its form. As long as the application produces any sound, the test is considered successfully completed.
"""

camera_prompt = """
## Task Scenario: Camera Access Testing
You are testing an application's camera access functionality. Your primary goal is to find and activate features that launch the device's camera.

## Background
Many applications provide access to the device's camera for taking photos, video calls, scanning QR codes, or augmented reality experiences. These features are typically accessed through specific buttons, menu options, or interaction flows.

## Testing Objective
Find and successfully launch the camera functionality within the application. Try the following approaches in order of priority:

1. Look for and tap any obvious camera icons, photo buttons, or video icons
2. Explore the main interface of the app, looking for areas that might relate to image/video capture
3. Check bottom navigation bars, floating action buttons, or top-right menu options for camera features
4. Look for camera-related functionality in profile, messaging, posting, or content creation areas
5. If the app has search functionality, try searching for terms like "camera", "photo", "scan", etc.
6. Check application settings for media, permissions, or content creation options

## Success Criteria
The test is considered successful when the application successfully launches the device's camera. This is typically indicated by:
- Camera preview screen appearing, showing a live feed
- System permission request for camera access appearing
- Photo/video capture controls becoming visible
- Interface transition to a camera capture mode

Once the camera is successfully launched (either front or rear camera), the test is considered complete. You do not need to actually capture photos or videos - just confirm that the camera has been activated.
"""

micro_prompt = """
## Task Scenario: Microphone Access Testing
You are testing an application's microphone access functionality. Your primary goal is to find and activate features that utilize the device's microphone.

## Background
Many applications provide features that require microphone access for voice recording, voice commands, voice calls, or audio input. These features are typically accessed through specific buttons, menu options, or interaction flows.

## Testing Objective
Find and successfully activate the microphone functionality within the application. Try the following approaches in order of priority:

1. Look for and tap any obvious microphone icons, voice recording buttons, or audio input indicators
2. Explore voice messaging or voice note features in communication apps
3. Check for voice search functionality, often indicated by microphone icons in search bars
4. Look for voice call or video call features in communication apps
5. Explore voice command or voice assistant features in the application
6. Check application settings for audio, microphone, or voice-related options
7. If the app has search functionality, try searching for terms like "voice", "record", "microphone", etc.

## Success Criteria
The test is considered successful when the application successfully activates the device's microphone. This is typically indicated by:
- Microphone permission request dialog appearing
- Voice recording or audio input interface becoming visible
- Audio level indicators or waveforms appearing
- Interface transition to a recording or listening mode
- Confirmation that the app is listening or recording

Once the microphone is successfully activated, the test is considered complete. You do not need to complete a full recording or voice interaction - just confirm that the microphone has been activated.
"""

keyboard_prompt = """
## Task Scenario: Keyboard Input Testing
You are testing an application's text input functionality. Your primary goal is to find and activate features that trigger the device's keyboard.

## Background
Most applications include text input fields for searching, messaging, form filling, or content creation. These input fields typically activate the device's keyboard when tapped.

## Testing Objective
Find and successfully trigger the keyboard within the application. Try the following approaches in order of priority:

1. Look for and tap any obvious text input fields, search bars, or message composition areas
2. Explore content creation features such as post creation, comment sections, or note-taking areas
3. Check for form fields in profile settings, account information, or registration areas
4. Look for search functionality in any section of the application
5. Explore messaging or communication features that would require text input
6. If the app has settings or configuration options, look for customizable fields that might accept text input

## Success Criteria
The test is considered successful when the application successfully triggers the device's keyboard. This is typically indicated by:
- On-screen keyboard appearing at the bottom of the screen
- Text cursor blinking in an input field
- Text input field becoming active or highlighted
- Placeholder text in the input field disappearing when tapped

Once the keyboard is successfully displayed, the test is considered complete. You do not need to complete text entry or form submission - just confirm that the keyboard has been activated.
"""


image_description_prompt = """
## Task
I have uploaded a screenshot of a mobile app interface followed by {component_count} images of clickable components from that interface.
Please analyze each component image in order and briefly describe its function (max 15 Chinese characters per description).

## Requirements
- You MUST provide exactly {component_count} descriptions in the exact order of the component images
- Return your answer as a Python list with exactly {component_count} strings
- Each description should be concise and functional
- Do not include any additional explanations

## Example response format
['返回按钮', '搜索框', '设置按钮', '添加设备']

Remember: Your response MUST contain exactly {component_count} descriptions in a list.
"""

select_prompt = """
## Task
I have uploaded a list of clickable components on the current page. Please select the best one based on the following description.

## Component List
{}

## Description
{}

## Instructions
- Analyze the component list and find the component that best matches the description
- Return ONLY the element_id number of the best matching component
- Do not include any explanations, just the number
- If no component matches well, return the closest match

Example response:
2
"""


next_event_prompt = """
## Test Scenario: 
{}
Note: The original test scenario is from Android platform and needs to be adapted to the HarmonyOS platform. There may be differences in UI layouts, element identifiers, and interaction patterns between these platforms.

## Clickable Elements on the Current Screen:
{}

## Operations Completed So Far:
{}

## Feedback and Suggestions from the Previous Operation:
{}

## Your Task
Based on the test scenario, the current screenshot, the list of clickable elements, the operations completed, 
and the feedback and suggestions from the previous operation, determine what the next operation should be.

Consider the following when making your decision:
1. Focus on functional intent rather than exact UI element matching, adapting to the current UI state.
2. Choose the most appropriate element that serves the same purpose as in the original scenario.
3. If the target element is not visible on the current screen, prioritize swiping operations to reveal more content before attempting other actions.
4. When swiping, consider both direction (vertical/horizontal) and context of what you're looking for, paying attention to visual cues like partial items at screen edges.
5. If exact elements are unavailable after swiping, look for alternatives with similar functionality.
6. Recognize equivalent functionality across different naming conventions (e.g., "屏幕超时", "自动锁屏", "休眠" may all refer to the same auto-lock functionality).
7. Avoid repeating operations that have already been executed, based on previous feedback.

## Available Operations
You can only choose from the following types of actions:
1. "click": Specify the element ID from the provided list
2. "swipe": Specify the direction ("up", "down", "left", "right")
3. "back": Press the back button

## Response Format
Return your decision strictly in the following JSON format, without any explanatory language:
{{"event_type": "click", "element_id": 3}}
{{"event_type": "swipe", "direction": "up"}}
{{"event_type": "back"}}
"""

# 5. "home": Return to the home screen (close the application)
# {{"event_type": "home"}}
# {{"event_type": "input", "element_id": 2, "text": "测试文本"}}
# 2. "input": Specify the element ID and the text to be entered


verify_prompt = """
## Scenario: 
{}

## Operations Performed
{}

## Interface Elements Before Operation
{}

## Interface Elements After Operation
{}

## Analysis Task
Please carefully analyze the screenshots and UI element changes before and after the operation, and strictly evaluate according to the following dimensions:

1. Historical Context:
   - Review all previously completed operations
   - Evaluate if the current operation logically follows previous steps
   - Check for any unnecessary repetition of operations

2. Goal Direction:
   - Whether the operation performed is moving in the correct direction toward the scenario goal
   - Whether there is any deviation from the scenario goal
   - If there is deviation, what specific aspects it manifests in

3. Interface Response:
   - Whether the interface has undergone significant changes (ignoring status information such as time and battery)
   - Whether the changes align with the expected operation results
   - If there are no changes, what might be the possible reasons

4. Goal Completion:
   - Considering all executed operations, whether the current state has FULLY completed ALL aspects of the goal described in the scenario
   - Whether ANY further operations are needed to achieve complete success
   - Specific concrete evidence that ALL success criteria have been met
   - Identify any missing elements or incomplete aspects of the goal

5. Termination Assessment:
   - Based on the scenario goal and operation sequence, determine if testing should conclude
   - If termination is appropriate, identify MULTIPLE specific completion indicators that are ALL present
   - If continuation is needed, specify remaining steps required

## Output Requirements
Please return the analysis results strictly in the following format:
{{
    "validity": true/false, // Whether the operation is valid (successfully executed, correct UI response, matches functional intent, and leads to reasonable state change)
    "goal_completion": true/false, // Whether the test scenario's objective has been FULLY achieved with CONCRETE EVIDENCE. Set to true ONLY if ALL success criteria are clearly met with no ambiguity. When in doubt, set to false.
    "analysis": "Detailed analysis of the operation's effectiveness, interface changes, and progress toward the test goal",
    "next_steps": "Suggested next steps based on the current state, including correction if the current path is incorrect"
}}

Ensure your analysis focuses on functional intent rather than exact UI matching, considering the cross-platform adaptation context. 
Be precise, objective, and base your evaluation on evidence from operation history, screenshots, and UI elements. 
If the current operation deviates from the test goal, clearly indicate this and provide correction suggestions.

IMPORTANT: When determining goal completion, be extremely conservative. Set "goal_completion" to true ONLY when you have clear, unambiguous evidence that ALL aspects of the test goal have been achieved. If there is ANY doubt or if ANY success criterion has not been definitively met, set "goal_completion" to false. The testing should continue until there is overwhelming evidence that the goal has been completely achieved.
"""



