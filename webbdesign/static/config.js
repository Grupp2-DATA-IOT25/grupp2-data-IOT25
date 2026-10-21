// OBS isLocal tilldelas automatiskt värdet true eller false beroende på om url:t är lokalt eller inte local url där websidan körs. 


const isLocal =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1";

const CONFIG = {
    environment: isLocal ? "test" : "production",

    apiUrls: {
        test: "/api/servers",
        production: "/api/servers"
    }
};



