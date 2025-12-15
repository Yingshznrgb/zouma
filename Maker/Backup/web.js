fetch('http://<raspberrypi-ip>:5000/display', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        imageUrl: 'http://your-web-server.com/output.jpg',
        text: '这里是智能体生成的描述'
    })
})
.then(response => response.json())
.then(data => console.log('树莓派返回:', data));
