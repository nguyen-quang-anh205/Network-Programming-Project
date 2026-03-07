#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h> 

void error(const char *msg) {
    perror(msg);
    exit(0);
}

int main(int argc, char *argv[]) {
    int sockfd, portno, n;
    struct sockaddr_in serv_addr;
    char buffer[256];

    // Kiểm tra xem người dùng đã truyền đủ IP và Port chưa [cite: 225, 227]
    if (argc < 3) {
       fprintf(stderr, "Cách dùng: %s <IP_Server> <Port>\n", argv[0]);
       exit(0);
    }

    // Đọc port từ tham số dòng lệnh argv[2] 
    portno = atoi(argv[2]);
    
    sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) error("ERROR opening socket");

    memset(&serv_addr, 0, sizeof(serv_addr));
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(portno);
    
    // Đọc IP Server từ tham số dòng lệnh argv[1]
    if (inet_pton(AF_INET, argv[1], &serv_addr.sin_addr) <= 0) {
        fprintf(stderr, "IP không hợp lệ\n");
        exit(0);
    }

    if (connect(sockfd, (struct sockaddr *) &serv_addr, sizeof(serv_addr)) < 0) 
        error("ERROR connecting");

    printf("Connected! Hãy nhập tin nhắn: ");
    memset(buffer, 0, 256);
    fgets(buffer, 255, stdin);
    
    n = write(sockfd, buffer, strlen(buffer));
    if (n < 0) error("ERROR writing to socket");

    close(sockfd);
    return 0;
}
