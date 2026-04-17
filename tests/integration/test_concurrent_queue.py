import queue
import threading


def test_it03_50_score_updates_no_deadlock():
    q = queue.Queue()
    received = []

    def producer():
        for i in range(50):
            q.put({"score": 75.0 + i * 0.1, "label": "SAFE"})

    def consumer():
        while True:
            try:
                item = q.get(timeout=2)
                received.append(item)
                q.task_done()
            except queue.Empty:
                break

    t_producer = threading.Thread(target=producer)
    t_consumer = threading.Thread(target=consumer)

    t_producer.start()
    t_consumer.start()

    t_producer.join(timeout=5)
    t_consumer.join(timeout=5)

    assert not t_producer.is_alive(), "producer thread deadlocked"
    assert not t_consumer.is_alive(), "consumer thread deadlocked"
    assert len(received) == 50
