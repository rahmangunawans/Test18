from app import app  # noqa: F401
from flask import render_template_string

@app.route('/test_embed_debug.html')
def test_embed_debug():
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Embed Testing - AniFlix</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white p-8">
    <h1 class="text-2xl font-bold mb-6">Server 2 Embed Testing</h1>
    
    <div class="space-y-8">
        <!-- Test 1: mp4upload -->
        <div>
            <h2 class="text-xl mb-4">Test 1: mp4upload.com</h2>
            <div class="bg-black rounded-lg" style="height: 480px;">
                <iframe 
                    src="https://www.mp4upload.com/embed-32m2mnpv72pb.html" 
                    frameborder="0" 
                    marginwidth="0" 
                    marginheight="0" 
                    scrolling="no" 
                    width="100%" 
                    height="480"
                    allowfullscreen
                    style="width: 100%; height: 100%;">
                </iframe>
            </div>
        </div>

        <!-- Test 2: YouUpload -->
        <div>
            <h2 class="text-xl mb-4">Test 2: YouUpload.com</h2>
            <div class="bg-black rounded-lg" style="height: 480px;">
                <iframe 
                    src="https://www.yourupload.com/embed/3f3phMUGr80Q" 
                    frameborder="0" 
                    width="100%" 
                    height="480"
                    allowfullscreen
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen"
                    style="width: 100%; height: 100%;">
                </iframe>
            </div>
        </div>

        <!-- Test 3: Working Example (Streamable) -->
        <div>
            <h2 class="text-xl mb-4">Test 3: Working Embed Example</h2>
            <div class="bg-black rounded-lg" style="height: 480px;">
                <iframe 
                    src="https://streamable.com/e/123456" 
                    frameborder="0" 
                    width="100%" 
                    height="480"
                    allowfullscreen
                    style="width: 100%; height: 100%;">
                </iframe>
            </div>
        </div>

        <!-- Test 4: Direct links -->
        <div>
            <h2 class="text-xl mb-4">Test 4: Direct Links</h2>
            <div class="space-y-2">
                <a href="https://www.mp4upload.com/embed-32m2mnpv72pb.html" target="_blank" 
                   class="block bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">
                    Open mp4upload in new tab
                </a>
                <a href="https://www.yourupload.com/embed/3f3phMUGr80Q" target="_blank" 
                   class="block bg-green-600 hover:bg-green-700 px-4 py-2 rounded">
                    Open YouUpload in new tab
                </a>
            </div>
        </div>
    </div>

    <script>
        console.log('Embed test page loaded');
        
        // Monitor iframe loading
        const iframes = document.querySelectorAll('iframe');
        iframes.forEach((iframe, index) => {
            iframe.onload = () => {
                console.log(`Iframe ${index + 1} loaded:`, iframe.src);
            };
            iframe.onerror = () => {
                console.error(`Iframe ${index + 1} error:`, iframe.src);
            };
        });
    </script>
</body>
</html>
    ''')

# Register VIP download blueprint
from vip_downloads import vip_downloads_bp
app.register_blueprint(vip_downloads_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
