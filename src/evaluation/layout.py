"""Line detection recall and reading-order errors against annotated polygons."""
import cv2
import numpy as np


def evaluate_layout(predicted, reference, page_size, transform=None, threshold=.5):
    """Reference polygons are supplied in reading order in original normalized-image pixels.

    A bounded raster computes polygon IoU. Greedy one-to-one matches above the
    threshold define recall; order errors count inversions among matched lines.
    """
    width,height=page_size
    scale=min(1,1000/max(width,height))
    shape=(max(1,round(height*scale)),max(1,round(width*scale)))
    matrix=np.asarray(transform if transform is not None else np.eye(3))
    def mask(polygon,original=False):
        points=np.asarray(polygon,dtype=float)
        if original:
            points=np.column_stack([points,np.ones(len(points))])@matrix.T
            points=points[:,:2]/points[:,2:]
        result=np.zeros(shape,np.uint8)
        cv2.fillPoly(result,[np.rint(points*scale).astype(np.int32)],1)
        return result.astype(bool)
    predictions=[mask(p) for p in predicted]
    references=[mask(p,True) for p in reference]
    candidates=[]
    for i,pred in enumerate(predictions):
        for j,truth in enumerate(references):
            union=np.logical_or(pred,truth).sum()
            iou=float(np.logical_and(pred,truth).sum()/union) if union else 0
            if iou>=threshold:
                candidates.append((iou,i,j))
    used_predictions,used_references=set(),set()
    matches=[]
    for iou,i,j in sorted(candidates,reverse=True):
        if i not in used_predictions and j not in used_references:
            used_predictions.add(i);used_references.add(j);matches.append((i,j))
    order=[j for i,j in sorted(matches)]
    inversions=sum(a>b for i,a in enumerate(order) for b in order[i+1:])
    return {'line_recall':len(matches)/len(reference) if reference else None,
            'line_precision':len(matches)/len(predicted) if predicted else None,
            'reading_order_inversions':inversions,'matched_lines':len(matches),
            'reference_lines':len(reference),'iou_threshold':threshold,'raster_long_edge':max(shape)}
