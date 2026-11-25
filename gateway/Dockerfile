# KrakenD (edición comunitaria) con la configuración del clúster Rodar. La configuración sale de plantillas
# (krakend.tmpl + settings/) y de variables de entorno; la imagen es la misma en local y en Azure.
FROM krakend:3.0.5
COPY krakend.tmpl /etc/krakend/krakend.tmpl
COPY settings /etc/krakend/settings
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
ENV FC_ENABLE=1 FC_SETTINGS=/etc/krakend/settings
USER krakend
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://localhost:8080/health || exit 1
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
