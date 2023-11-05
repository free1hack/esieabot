// Creating the left stick (manager) for motors
const options = {
    zone: document.querySelector('.left_stick'),
    mode: 'static',
    position: { left: '50%', top: '50%' },
    color: '#36A9E1',
    size: 150,
};
const manager = nipplejs.create(options);

// Creating the right stick (manager2) for servos
const options2 = {
    zone: document.querySelector('.right_stick'),
    mode: 'static',
    position: { left: '50%', top: '50%' },
    color: '#36A9E1',
    size: 150,
    lockY: true,
};
const manager2 = nipplejs.create(options2);

var elem = document.documentElement;

// Storing previous value of axis to avoid sendind same data everytime
var previous_X = 0;
var previous_Y = 0;
var current_X = 0;
var current_Y = 0;
var previous_pitch = 0;
var current_pitch = 0;

// On right axis move event
manager2.on('move', function (evt, data) {
    if (((data.angle.degree <= 90) && (data.angle.degree > 0)) || ((data.angle.degree <= 360) && (data.angle.degree > 270))) {
        X = Math.cos(data.angle.radian) * data.distance;
        Y = Math.sin(data.angle.radian) * data.distance;
    }
    if (((data.angle.degree <= 180) && (data.angle.degree > 90)) || ((data.angle.degree <= 270) && (data.angle.degree > 180))) {
        X = -Math.cos(Math.PI - data.angle.radian) * data.distance;
        Y = Math.sin(Math.PI - data.angle.radian) * data.distance;
    }
    current_pitch = Y;
    // TODO: do yaw axis
});

// On crash, set to 0
manager2.on('end', function (evt, data) {
    current_pitch = 0;
});

// On left axis move event
manager.on('move', function (evt, data) {
    if (((data.angle.degree < 90) && (data.angle.degree > 0)) || ((data.angle.degree < 360) && (data.angle.degree > 270))) {
        X = Math.cos(data.angle.radian) * data.distance;
        Y = Math.sin(data.angle.radian) * data.distance;
    }
    if (((data.angle.degree < 180) && (data.angle.degree > 90)) || ((data.angle.degree < 270) && (data.angle.degree > 180))) {
        X = -Math.cos(Math.PI - data.angle.radian) * data.distance;
        Y = Math.sin(Math.PI - data.angle.radian) * data.distance;
    }
    current_X = X;
    current_Y = Y;

// On crash, set to 0
}).on('end', function (evt, data) {
    current_X = 0;
    current_Y = 0;
});

// Sending command to API every 50ms if there was any change
function sendCommand() {
    if (Math.abs(current_X - previous_X) > 15 || Math.abs(current_Y - previous_Y) > 15 || current_X == 0 && current_Y == 0 && previous_X != 0 && previous_Y != 0) {
        previous_X = current_X;
        previous_Y = current_Y;
        $.get("/command?x=" + current_X + "&y=" + current_Y + "&heartbeat=True", function (data, status) {
            // Do something with data
        });
    }
    if (current_pitch != 0 || current_pitch == 0 && previous_pitch != 0) {
        previous_pitch = current_pitch;
        $.get("/camera?pitch=" + current_pitch, function (data, status) { /* Do something */ });
    }
    setTimeout(sendCommand, 50);
}

// Sending an heartbeat every 2 seconds to the server
function sendHeartBeat() {
    $.get("/heartbeat", function (data, status) { /* Do something */ });
    setTimeout(sendHeartBeat, 2000);
}

sendCommand();
sendHeartBeat();