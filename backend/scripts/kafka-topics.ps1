$bootstrapServer = if ($env:KAFKA_BOOTSTRAP_SERVERS) { $env:KAFKA_BOOTSTRAP_SERVERS } else { "localhost:9092" }

kafka-topics --bootstrap-server $bootstrapServer --create --if-not-exists --topic ecommerce.products --partitions 3 --replication-factor 1
kafka-topics --bootstrap-server $bootstrapServer --create --if-not-exists --topic ecommerce.sales --partitions 3 --replication-factor 1

