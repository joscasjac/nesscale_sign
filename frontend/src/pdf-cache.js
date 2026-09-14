import { getDocument, GlobalWorkerOptions } from "pdfjs-dist";
import worker from "pdfjs-dist/build/pdf.worker.min.mjs?url";
GlobalWorkerOptions.workerSrc = worker;
const documents = new Map();
export function acquirePdf(url) {
	let entry = documents.get(url);
	if (!entry) {
		entry = { task: getDocument({ url, withCredentials: true }), users: 0 };
		documents.set(url, entry);
	}
	entry.users++;
	let released = false;
	return {
		promise: entry.task.promise,
		release() {
			if (released) return;
			released = true;
			if (--entry.users === 0) {
				documents.delete(url);
				entry.task.destroy();
			}
		},
	};
}
