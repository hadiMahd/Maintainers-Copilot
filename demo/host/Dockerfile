FROM nginx:1.27-alpine

COPY allowed/ /usr/share/nginx/html/allowed/
COPY blocked/ /usr/share/nginx/html/blocked/

ENV BACKEND_URL=http://localhost:8000
ENV WIDGET_ID=YOUR_WIDGET_ID

CMD ["sh", "-c", "find /usr/share/nginx/html -name '*.html' -exec sed -i \"s|BACKEND_URL|${BACKEND_URL}|g; s|YOUR_WIDGET_ID|${WIDGET_ID}|g\" {} + && nginx -g 'daemon off;'"]
