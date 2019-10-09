#python3 embeding_clustering_full_kmeans.py --embeding_file data/pcaUT29-15 --modify false/true --daily false/true  --cluster_number 7 --method merge/not_merge --merge_type single/multi --ADD_file imgname2ADD > daily_merge_7ClusAll
# the file for this script should be image_name va1l val2.... valn.
from sklearn.cluster import KMeans
from sklearn.cluster import AgglomerativeClustering
from sklearn.cluster import DBSCAN
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.cluster import SpectralClustering
import matplotlib.pyplot as plt
import sys
import numpy as np
import csv
import ast
import datetime
import pickle
import argparse
from operator import itemgetter 
from functools import reduce
from scipy.spatial import distance
import math
#from kneed import KneeLocator
## to use itemgetter(the indices seperated by ,)(the list name)



def key_func(x):
    # For some year like 2011 the year is 2 digits so the date format should ne %m%d%y but for others like 2015 it should be %m%d%Y
    try:
        if '(' in x:     
            return datetime.datetime.strptime(x.split('D_')[-1].split('(')[0].strip().replace('_',''), '%m%d%y')
        else: 
            return datetime.datetime.strptime(x.split('D_')[-1].split('.')[0].strip().replace('_',''), '%m%d%y')
    except:
        print(x)
        import bpython
        bpython.embed(locals())
        exit()

def sort_dates(donors2imgs): #sorts the dates by getting a list of img_names for each donor and sorting that
    for key in donors2imgs:
        donors2imgs[key] = sorted(donors2imgs[key], key=key_func)
    return donors2imgs

def convert_to_time(img_name):
    if '(' not in img_name:
        date = img_name.split('/')[-1].split("D_")[1].split('.JPG')[0]
    else:
        date = img_name.split('/')[-1].split("D_")[1].split(' ')[0]
    # this is the format and we only need the date part UT06-12D_07_26_12 (21).JPG
    date = date.replace('_', '') # to remove the '_'
    return datetime.datetime.strptime(date, '%m%d%y') #formated as date

def cal_day_from_deth(donors2imgs_sorted):
    for key in donors2imgs_sorted:
        day2imgs = {} 
        first_img = True
        for img in donors2imgs_sorted[key]:
            if first_img == True:
                start_time = convert_to_time(img)
                first_img = False
            img_time = convert_to_time(img)
            time_from_start = (img_time - start_time).days
            if time_from_start not in day2imgs:
                day2imgs[time_from_start] = []
            day2imgs[time_from_start].append(img)
        donors2imgs_sorted[key] = day2imgs 
    return donors2imgs_sorted 
    # this a dictionary with each donor_id as keys and values are another 
    #dictionary with keys being xth days since day one and the values are a 
    #list of images that belong to day xth for that donor.
def save_to_pickle(dict_, file_name):
    f = open(file_name + '.pkl', 'wb')
    pickle.dump(dict_, f)
    #f.colse()

def cal_cluster2img(labels, names):
        cluster2img = {}
        for index, label in enumerate(labels):
            if label not in cluster2img:
                cluster2img[label] = []
            cluster2img[label].append(names[index])
        return cluster2img

def find_cluster_num(vectors):
    potential_cluster_num = np.arange(2, 20, 1) # arange(start, stop, step)
    silhouette_scores = []
    for c in potential_cluster_num:
        ## kmean cluster 
        kmeans = KMeans(n_clusters = c)
        kmeans.fit(vectors)
        labels = kmeans.predict(vectors)
        score = silhouette_score(vectors, labels)
        silhouette_scores.append(score)
        print("[INFO] number of clusters is {} and the silhouette score is {}".format(c, score))
    num_clusters = silhouette_scores.index(max(silhouette_scores)) + 2 #because I started with 2 for potential_cluster_num
    print("best cluster number is ", num_clusters)
    return num_clusters

def cluster(donor2img2embeding, donor2day2img):
    for donor in donor2img2embeding:
        img_names = []
        vectors = []
        for img in donor2img2embeding[donor]:
            img_names.append(img.replace('JPG','icon.JPG').replace(' ',' '))
            vectors.append(donor2img2embeding[donor][img])
        vectors = np.array(vectors)
        vectors = vectors / vectors.max(axis=0)
        ## kmeans:
        kmeans = KMeans(n_clusters = num_clusters)
        kmeans.fit(vectors)
        labels = kmeans.predict(vectors)
        '''
        ######### Agglomerative ######
        agglomerative = AgglomerativeClustering(n_clusters = num_clusters, linkage='single')
        agglomerative.fit(list(vectors))
        labels = agglomerative.labels_#predict(vectors)
    '''
        for index, label in enumerate(labels):
            print(img_names[index] , ":" , donor, "_",  label)

def daily_clustering(donor2img2embeding, donor2day2img):
    img_names = []
    vectors = []
    days_data = {}
    for donor in donor2day2img:
        for day in donor2day2img[donor]:
            if day not in days_data:
                days_data[day] = [0, 0]
                days_data[day][0] = [] # this would contain the image_names for this day
                days_data[day][1] = [] # this would contain the embedings for this day
            days_data[day][0].extend(donor2day2img[donor][day]) # used extend beacuse donor2day2img[donor][day] is a list
            for img in donor2day2img[donor][day]:
                days_data[day][1].append(donor2img2embeding[donor][img])

    for day in days_data:
        vectors = days_data[day][1]
        vectors = np.array(vectors)
        #num_clusters = 15 #find_cluster_num(vectors)

        if len(days_data[day][0]) < 2* num_clusters:
            continue

        kmeans = KMeans(n_clusters = num_clusters)
        kmeans.fit(vectors)
        labels = kmeans.predict(vectors)
        #score = silhouette_score(vectors, labels)

        for index, label in enumerate(labels):
            print(days_data[day][0][index] , ":" , day, "_", label)


def cluster_dist(labels, kmeans, vectors):
    for l1 in np.unique(labels):
        dist_list = []
        for l2 in np.unique(labels):
            dist = distance.euclidean(kmeans.cluster_centers_[l1], kmeans.cluster_centers_[l2]) # find the distance between the centers
            #dist_list.append(dist)


# This function will put all images for each day across donor and then cluster per day and then merge each day to the next
def daily_clustering_per_multidonor(donor2img2embeding, donor2day2img):

    day2clus2emb = {}#each cluster will have one vector which is the center/average of the ones belonging to it
    day2clus2imgs = {} # each claster (key) would have a value of the lsit of image names belonging to it

    img_names = []
    vectors = []
    days_data = {}
    for donor in donor2day2img:
        for day in donor2day2img[donor]:
            if day not in days_data:
                days_data[day] = [0, 0]
                days_data[day][0] = [] # this would contain the image_names for this day
                days_data[day][1] = [] # this would contain the embedings for this day
            days_data[day][0].extend(donor2day2img[donor][day]) # used extend beacuse donor2day2img[donor][day] is a list
            for img in donor2day2img[donor][day]:
                days_data[day][1].append(donor2img2embeding[donor][img])

    days = []
    for day in days_data:
        vectors = days_data[day][1]
        img_names = days_data[day][0]
        vectors = np.array(vectors)

        if len(vectors) < 2* num_clusters :
            continue
        else:
            days.append(day)
            if day not in day2clus2emb:
                day2clus2emb[day] = {}
                day2clus2imgs[day] = {}

            kmeans = KMeans(n_clusters = num_clusters)
            kmeans.fit(vectors)
            labels = kmeans.predict(vectors)
            
            #score = silhouette_score(vectors, labels)
            cluster_ids = np.array(labels)
            clus2embs = {}
            clus2imgs = {}
            for clus in range(num_clusters):
                clus_index = np.where(cluster_ids == clus)[0] #get the indices for the cluster id = clus

                clus2embs[clus] = kmeans.cluster_centers_[clus]
                day2clus2emb[day] = clus2embs
                temp = itemgetter(*clus_index)(img_names)
                clus2imgs[clus] = list(temp) if type(temp) is tuple else [temp]
                day2clus2imgs[day] = clus2imgs

            for index, label in enumerate(labels):
                print(img_names[index] , ":" ,donor, "_", day, "_", label)
    find_associations(days, day2clus2imgs, day2clus2emb, donor)# the donor is not needed realy in this case. That is for single donor merging
    return day2clus2emb

def streaming_cluster(donor2img2embeding, donor2day2img):
    n_clusters = 7

    # For each donor
    for donor in donor2day2img:
        days = list(donor2day2img[donor].keys())
        days.sort()

        # Window information
        start = 0
        window_size = 3
        end = start + window_size

        # Store all window clusters
        window_clusters_imgs = []
        
        while end < len(days):
            img_names = []
            embeddings = []
            # For every day in our window
            for day_index in range(start, end): 
                day = days[day_index]
                # Grab all the features in this window for this donor
                for img in donor2day2img[donor][day]:
                    img_names.append(img)
                    embeddings.append(donor2img2embeding[donor][img])

            embeddings = np.array(embeddings)
            embeddings = embeddings / embeddings.max(axis = 0)
            kmeans = SpectralClustering(n_clusters = n_clusters, affinity='nearest_neighbors', assign_labels='kmeans')
            labels = kmeans.fit_predict(embeddings)
            #labels = kmeans.predict(embeddings)

            window_cluster = {}
            for i, label in enumerate(labels):
                if label in window_cluster: 
                    window_cluster[label].append(img_names[i])
                else: 
                    window_cluster[label] = [img_names[i]]

            window_clusters_imgs.append(window_cluster)

            start += 1
            end = start + window_size

        # Merge the clusters
        i = 0
        merges = []
        while i < len(window_clusters_imgs) - 1:
            merged = []
            first_clusters = window_clusters_imgs[i] # For the ith window
            second_clusters = window_clusters_imgs[i + 1] # For the (i + 1)th window
            for c1_index, c1_imgs in first_clusters.items(): 
                max_overlap = 0
                max_overlap_index = -1
                for c2_index, c2_imgs in second_clusters.items():
                    overlap = len(set(c1_imgs).intersection(set(c2_imgs)))
                    if overlap > max_overlap: 
                        max_overlap = overlap
                        max_overlap_index = c2_index
            

                merged.append([c1_index , max_overlap_index])
            merges.append(merged)
            i += 1
            
            
        def findNext(pair, bin_index):
            if bin_index >= len(merges):
                return []
            else: 
                for group in merges[bin_index]:
                    if group[0] == pair[1]: 
                        # found the associated pair
                        return [group[1]] + findNext(group, bin_index + 1)
        groups  = []

        import bpython
        bpython.embed(locals())

        for i, pair in enumerate(merges[0]):
            temp = pair + findNext(pair, 1)
            # temp is a list [a, b, c, ...z] where its index is the bin_index and its values are cluster numbers

            group = []#{'cluster': [], 'day': 0}
            # group is a temporary super-cluster that is used to break the chains 

            for window_index, cluster in enumerate(temp):
                # skip last one since it'll be out of bounds
                group.append(cluster)
                if window_index == len(temp) - 1: 
                    groups.append(group)

        clusters = []
        for group in groups:
            images = []
            for window_index, cluster_index in enumerate(group): 
                images += window_clusters_imgs[window_index][cluster_index]
            clusters.append(sorted(images, key = key_func))
        for i, imgs in enumerate(clusters):
            for img in imgs:
                print(img, ":",donor,"_", i) 

def cosine_similarity(v1,v2):
    "compute cosine similarity of v1 to v2: (v1 dot v2)/{||v1||*||v2||)"
    sumxx, sumxy, sumyy = 0, 0, 0
    for i in range(len(v1)):
        x = v1[i]; y = v2[i]
        sumxx += x*x
        sumyy += y*y
        sumxy += x*y
    return sumxy/math.sqrt(sumxx*sumyy)

def overlap_merge(all_sims):
    no_more_merge = False
    while no_more_merge == False:
        merged_dict = {}
        seen = []
        all_sims_keys = list(all_sims.keys())
        no_more_merge = True
        for key1 in all_sims_keys:
            if key1 not in seen:
                if key1 not in merged_dict :
                    merged_dict[key1] = list(set(all_sims[key1]))#to remove the duplicates
                for key2 in all_sims_keys:
                    if key1 != key2:
                        intersect = len(set(all_sims[key1]).intersection(set(all_sims[key2])))
                        if intersect != 0:
                            no_more_merge = False
                            merged_dict[key1].extend(list(set(all_sims[key2])))
                            merged_dict[key1] = sorted(merged_dict[key1], key = key_func)
                            seen.append(key2)
        all_sims = merged_dict
    return all_sims 
#########################################################################
def find_tail_head(all_sims, key1, key2):
    list1 = sorted(all_sims[key1], key = key_func)
    list2 = sorted(all_sims[key2], key = key_func)
    sequence1 = []
    sequence2 = []
    if len(list1) > 0 and len(list2) > 0:
        if convert_to_time(list1[0]) <  convert_to_time(list2[0]) and \
            convert_to_time(list1[-1]) >  convert_to_time(list2[0]):

            sequence1 = list1
            sequence2 = list2        
        else:
            sequence1 = list2
            sequence2 = list1        

        head = tail = []
        
        sequence1_times = [x.split("os//")[1].split()[0] for x in sequence1]
        sequence2_times = [x.split("os//")[1].split()[0] for x in sequence2]
        time_overlap = list(set(sequence1_times).intersection(set(sequence1_times)))

        tail = [x for x in sequence1 if x.split("os//")[1].split()[0] in time_overlap]
        head = [x for x in sequence2 if x.split("os//")[1].split()[0] in time_overlap]

        sequence1 = tail
        sequence2 = head

        tail_size = min(len(sequence1), len(sequence2))

        if tail_size == 1:
            tail = [sequence1[-1]]
            head = [sequence2[0]]
        else:
            tail = sequence1[-tail_size:]
            head = sequence2[:tail_size]
        '''
        min_size = min(len(sequence1), len(sequence2))
        tail_size = 0
        if len(sequence1) == min_size and min_size < 6:
            tail = sequence1
            tail_size = len(sequence1)
            head = sequence2[:tail_size] 
            ## the head of the target sequence to see if merge

        
        if len(sequence2)  == min_size and min_size < 6:
            head = sequence2
            tail_size = len(sequence2)
            tail = sequence1[-tail_size:] # the tail of the base sequence

        if len(head) == 0 and len(tail) == 0:     
            tail_size = min(len(sequence1), len(sequence2))// 3 # only one third
            tail = sequence1[-tail_size:] # the tail of the base sequence
            head = sequence2[:tail_size] ## the head of the target sequence to see if merge
        '''
    return head, tail, tail_size 
    
##########################################################################
def similarity_merge(all_sims, donor2img2embeding, donor2day2img, donor):
    no_more_merge = False
    while no_more_merge == False:
        merged_dict = {}
        seen = []
        all_sims_keys = list(all_sims.keys())
        no_more_merge = True

        for key1 in all_sims_keys:
            if key1 in seen:
                continue

            if key1 not in merged_dict :
                # to remove the duplicates
                merged_dict[key1] = list(set(all_sims[key1]))

            one2nsimi = []
            for key2 in all_sims_keys:
                if all_sims_keys.index(key2) <= all_sims_keys.index(key1):
                    continue
                head, tail, tail_size = find_tail_head(all_sims, key1, key2)
                if tail_size >= 1 :
                    similarity = []
                    for img_index in range(tail_size):
                        emb1 = donor2img2embeding[donor][tail[img_index]]
                        emb2 = donor2img2embeding[donor][head[img_index]]
                        simi = cosine_similarity(emb1, emb2)
                        similarity.append(simi)
                    sub_seq_simi = sum(similarity) / tail_size
                    one2nsimi.append([key2,sub_seq_simi])
            if len(one2nsimi) > 0:
                one2nsimi = sorted(one2nsimi, key=lambda x: x[1], reverse=True)
                val = max(one2nsimi[0][1], 0.5)
                if one2nsimi[0][1] >= val:
                    #one2nsimi.append([key2,sub_seq_simi])
                    no_more_merge = False
                    merged_dict[key1].extend(list(set(all_sims[one2nsimi[0][0]])))
                    merged_dict[key1] = sorted(merged_dict[key1], key = key_func)
                    seen.append(one2nsimi[0][0])
        all_sims = merged_dict
    print_(merged_dict, donor)

####################################################################
def add_to_similarity_dict(all_sims, similarities, key):#, ratio):
    similarities = sorted(similarities, key=lambda x: x[1], reverse=True)
    max_ = similarities[0][1]
    threshold = max(0.99 * max_, 0.40)
    for ind, pair in enumerate(similarities):
        if pair[1] >= threshold:
            if key not in all_sims:
                all_sims[key] = []
            all_sims[key].append(pair[0])
    return all_sims


##################################################################
def print_(all_sims, donor):
    label = 0
    for key in all_sims:
        label = label + 1
        for img in all_sims[key]:
            temp = img.replace('JPG', 'icon.JPG: ')
            print(temp + donor + "_" + str(label))

#################################################################
def sequence_finder(donor2img2embeding, donor2day2img):

    for donor in donor2img2embeding:
        #if donor == 'UT16-13D':
        days = list(donor2day2img[donor].keys())
        days.sort()
        all_embs = donor2img2embeding[donor]
        all_sims = {} #key = imgs, value = [[im1, dist],im2, dit[],...]

        window = 5
        for i in range(window, len(days)-window):
            imgs = donor2day2img[donor][days[i]] # images for day = days[i]

            for img in imgs:
                emb = all_embs[img]
                key = img
                for seen in all_sims:
                    for x in all_sims[seen]:
                        if img ==  x: # if it is one of the matched ones
                            key = seen
                    
                day_current_imgs = donor2day2img[donor][days[i]]
                similarities = []
                for day_current_img in day_current_imgs:
                    emb2 = all_embs[day_current_img] 
                    sim = cosine_similarity(emb, emb2)
                    similarities.append([day_current_img, sim])
                all_sims = add_to_similarity_dict(all_sims, similarities, key)

                for w in range(1, window + 1):
                    day_before_imgs = donor2day2img[donor][days[i-w]]
                    day_after_imgs = donor2day2img[donor][days[i+w]]
                    similarities = []
                    for day_before_img in day_before_imgs:
                        emb2 = all_embs[day_before_img] 
                        sim = cosine_similarity(emb, emb2)
                        similarities.append([day_before_img, sim])
                    all_sims = add_to_similarity_dict(all_sims, similarities, key)

                    similarities = []
                    for day_after_img in day_after_imgs:
                        emb2 = all_embs[day_after_img] 
                        sim = cosine_similarity(emb, emb2)
                        similarities.append([day_after_img, sim])
                    all_sims = add_to_similarity_dict(all_sims, similarities, key) 

        #print_(all_sims, donor)
        all_sims = overlap_merge(all_sims)
        print_(all_sims, donor)

        #similarity_merge(all_sims, donor2img2embeding, donor2day2img, donor)

###############################################################################
def clustering_per_donor_per_stage(donor2img2embeding, donor2day2img):
    for donor in donor2day2img:
        day2clus2emb = {}#each cluster will have one vector which is the center/average of the ones belonging to it
        day2clus2imgs = {} # each claster (key) would have a value of the lsit of image names belonging to it
        days = list(donor2day2img[donor].keys())
        days.sort()
        multi_days_vecctors = []
        multi_days_imgnames = []
        all_centers_per_donor = []
        all_clustered_imgs_per_donor = []

        for day in days:
            vectors = []
            img_names = []
            imgs = donor2day2img[donor][day]
            for img in imgs:
                vectors.append(donor2img2embeding[donor][img]) 
                img_names.append(img.replace('JPG','icon.JPG'))

            #vectors = np.array(vectors)
            multi_days_vecctors.append(vectors)
            multi_days_imgnames.append(img_names)

        daily_vects = []
        average_dist = []

        for vects in multi_days_vecctors:
            ave_vects = np.mean(np.array(vects), axis=0)
            daily_vects.append(ave_vects)

        new_vectors = []
        new_imgnames = []

        for i in range(len(daily_vects) - 1):#daily_vects = average of the vectors per day = one average vector per day
            dist = distance.euclidean(daily_vects[i], daily_vects[i+1])
            if len(average_dist) == 0:
                average_dist.append(dist)
            if np.abs(dist - np.mean(np.array(average_dist))) < np.mean(np.array(average_dist))/(i+1): 
                new_vectors.extend(v for v in multi_days_vecctors[i])
                new_imgnames.extend(im for im in multi_days_imgnames[i])
            else:
                new_vectors.extend(v for v in multi_days_vecctors[i])
                new_imgnames.extend(im for im in multi_days_imgnames[i])
                
                new_vectors = np.array(new_vectors)
                new_vectors = new_vectors / new_vectors.max(axis=0)
                ######## kmeans ##########
                kmeans = KMeans(n_clusters = num_clusters)
                kmeans.fit(new_vectors)
                labels = kmeans.predict(new_vectors)

                ######### Agglomerative ######
                '''
                agglomerative = AgglomerativeClustering(n_clusters = num_clusters, linkage='single')
                agglomerative.fit(list(vectors))
                labels = agglomerative.labels_#predict(vectors)
                '''

                cluster_ids = np.array(labels)
                clus2embs = {}
                clus2imgs = {}
                for clus in range(num_clusters):
                    clus_index = np.where(cluster_ids == clus)[0] #get the indices for the cluster id = clus
                    '''
                    ##### Agglo #### 
                    clus_embs = itemgetter(*clus_index)(list(new_vectors)) #find all embedings for the cluster. it's tuple
                    clus_embs_sum = reduce(lambda a, b: a+b, clus_embs) #get the average for the embedings for cluster = clus
                    clus_embs_ave = clus_embs_sum / len(clus_embs)
                    clus2embs[clus] = clus_embs_ave
                    '''
                    ### kmeans ####
                    clus2embs[clus] = kmeans.cluster_centers_[clus] # the center for clus
                    temp = itemgetter(*clus_index)(new_imgnames)
                    clus2imgs[clus] = list(temp) if type(temp) is tuple else [temp] #only images in clus 
    
                all_centers_per_donor.append(clus2embs) #each eleman is for one bin_
                all_clustered_imgs_per_donor.append(clus2imgs)

                #for index, label in enumerate(labels):
                #    print(new_imgnames[index] , ":" ,donor,"_", i,"_", label)
                new_vectors = []
                average_dist = []
                new_imgnames = []
        

        merges = []
        num_breaks = len(all_centers_per_donor)
        for bin_ in range(num_breaks - 1):
            all_dists = []
            for clus1 in range(num_clusters):
                for clus2 in range(num_clusters):
                    row = [] # row = clus1, clus2, distance
                    try:
                        dist = distance.euclidean(all_centers_per_donor[bin_][clus1], all_centers_per_donor[bin_ + 1][clus2])
                    except KeyError: 
                        print('KeyError')
                        import bpython
                        bpython.embed(locals())
                        exit()
                    row.append(clus1)
                    row.append(clus2)
                    row.append(dist) 
                    all_dists.append(row)
            seen1 = set()
            seen2 = set()
            merged = []

            match_dists = []
            #the following loop is to have a list of [x1,x2] called merged to say x1 got merged to x2 
            for i, l in enumerate(sorted(all_dists, key=lambda x: x[2], reverse=False)):
                if l[0] not in seen1 and l[1] not in seen2: 
                    merged.append([l[0], l[1]])
                    match_dists.append(l[2])
                    seen1.add(l[0])
                    seen2.add(l[1])
            merges.append(merged)

        def findNext(pair, bin_index):
            if bin_index >= len(merges):
                return []
            else: 
                for group in merges[bin_index]:
                    if group[0] == pair[1]: 
                        # found the associated pair
                        return [group[1]] + findNext(group, bin_index + 1)

        groups  = []
        for i, pair in enumerate(merges[0]):
            temp = pair + findNext(pair, 1)
            # temp is a list [a, b, c, ...z] where its index is the bin_index and its values are cluster numbers

            group = []#{'cluster': [], 'day': 0}
            # group is a temporary super-cluster that is used to break the chains 

            for bin_index, cluster in enumerate(temp):
                # skip last one since it'll be out of bounds
                group.append(cluster)
                if bin_index == len(temp) - 1: 
                    groups.append(group)
                    continue

        clusters = []
        for group in groups:
            images = []
            for bin_index, cluster_index in enumerate(group): 
                images += all_clustered_imgs_per_donor[bin_index][cluster_index]
            clusters.append(sorted(images, key = key_func))
        for i, imgs in enumerate(clusters):
            for img in imgs:
                print(img, ": merged_",donor,"_", i) 
    return day2clus2emb
############################################################## 
# This clusters images of one day per donor and then merges them
##############################################################

def daily_clustering_per_donor(donor2img2embeding, donor2day2img):
    for donor in donor2day2img:
        day2clus2emb = {}#each cluster will have one vector which is the center/average of the ones belonging to it
        day2clus2imgs = {} # each claster (key) would have a value of the lsit of image names belonging to it
        days = []
        for day in donor2day2img[donor]:
            vectors = []
            img_names = []
            imgs = donor2day2img[donor][day]
            for img in imgs:
                vectors.append(donor2img2embeding[donor][img]) 
                img_names.append(img.replace('JPG','icon.JPG'))

            vectors = np.array(vectors)
            #normalize
            #vectors = vectors / vectors.max(axis=0)

            if len(vectors) < 1.5 * num_clusters :
                continue
            else:
                days.append(day)
                if day not in day2clus2emb:
                    day2clus2emb[day] = {}
                    day2clus2imgs[day] = {}

                '''
                #### KMeans ###########
                kmeans = KMeans(n_clusters = num_clusters)
                kmeans.fit(vectors)
                labels = kmeans.predict(vectors)
                '''
                ######### Agglomerative ######
                agglomerative = AgglomerativeClustering(n_clusters = num_clusters, linkage='single')
                agglomerative.fit(list(vectors))
                labels = agglomerative.labels_#predict(vectors)

                #score = silhouette_score(vectors, labels)
                #print(score)
                cluster_ids = np.array(labels)
                clus2embs = {}
                clus2imgs = {}
                for clus in range(num_clusters):
                    clus_index = np.where(cluster_ids == clus)[0] #get the indices for the cluster id = clus

                    clus_embs = itemgetter(*clus_index)(list(vectors)) #find all embedings for the cluster. it's tuple
                    clus_embs_sum = reduce(lambda a, b: a+b, clus_embs) #get the average for the embedings for cluster = clus
                    clus_embs_ave = clus_embs_sum / len(clus_embs)
                    clus2embs[clus] = clus_embs_ave

                    #clus2embs[clus] = kmeans.cluster_centers_[clus]
                    day2clus2emb[day] = clus2embs
                    temp = itemgetter(*clus_index)(imgs)
                    clus2imgs[clus] = list(temp) if type(temp) is tuple else [temp]
                    day2clus2imgs[day] = clus2imgs

                '''
                for index, label in enumerate(labels):
                    print(img_names[index] , ":" ,donor, "_", day, "_", label)
                '''
        find_associations(days, day2clus2imgs, day2clus2emb, donor)
    return day2clus2emb

def find_associations(days, day2clus2imgs, day2clus2emb, donor):
    days.sort()
    num_days = len(days)
    merges = []
    #day = days[0]

    all_day_dists = {}
    all_match_dists = []

    for index in range(num_days - 1):
        day = days[index]
        next_day = days[index + 1]
        all_dists = []
        for clus1 in range(num_clusters):
            for clus2 in range(num_clusters):
                row = [] # row = clus1, clus2, distance
                try:
                    dist = distance.euclidean(day2clus2emb[day][clus1], day2clus2emb[next_day][clus2])
                except KeyError: 
                    print('KeyError')
                    import bpython
                    bpython.embed(locals())
                    exit()
                row.append(clus1)
                row.append(clus2)
                row.append(dist) 
                all_dists.append(row)
        '''
        for key in clusters:
            for img in clusters[key]:
                print(img, ": merged_", key)
        '''
        seen1 = set()
        seen2 = set()
        merged = []
        
        all_day_dists[index] = {(x[0], x[1]): x[2] for x in all_dists}

        match_dists = []
        #the following loop is to have a list of [x1,x2] called merged to say x1 got merged to x2 
        for i, l in enumerate(sorted(all_dists, key=lambda x: x[2], reverse=False)):
            if l[0] not in seen1 and l[1] not in seen2: 
                merged.append([l[0], l[1]])
                match_dists.append(l[2])
                seen1.add(l[0])
                seen2.add(l[1])
        all_match_dists.append(match_dists)
        merges.append(merged)

    std_ = np.std(np.array(all_match_dists))

    def findNext(pair, day_index):
        if day_index >= len(merges):
            return []
        else: 
            for group in merges[day_index]:
                if group[0] == pair[1]: 
                    # found the associated pair
                    return [group[1]] + findNext(group, day_index + 1)

    groups  = []
    for i, pair in enumerate(merges[0]):
        day = 0
        temp = pair + findNext(pair, 1)
        # temp is a list [a, b, c, ...z] where its index is the day and its values are cluster numbers

        group = {'cluster': [], 'day': 0}
        # group is a temporary super-cluster that is used to break the chains 

        for day_index, cluster in enumerate(temp):
            # skip last one since it'll be out of bounds
            group['cluster'].append(cluster)
            if day_index == len(temp) - 1: 
                groups.append(group)
                continue

            next_cluster = temp[day_index + 1]
            _distance = all_day_dists[day_index][(cluster, next_cluster)]
            if _distance > 2*std_: 
                groups.append(group)
                group = {'cluster': [], 'day': day_index + 1} 

        #groups.append(temp)
    clusters = []
    for group in groups:
        images = []
        for day, cluster_index in enumerate(group['cluster']): 
            day = days[day + group['day']] # shift by start day
            images += day2clus2imgs[day][cluster_index]
        clusters.append(sorted(images, key = key_func))
    for i, imgs in enumerate(clusters):
        for img in imgs:
            print(img.replace('.JPG', '.icon.JPG'), ": merged_",donor,"_", i) 
    '''
    for merging_clusters in merged: #merging clusters are akways 2. The id of the cluster is always determined by the first day
        if merging_clusters[0] not in clusters:
            clusters[merging_clusters[0]] = day2clus2imgs[day][merging_clusters[0]] 
    '''      

def cal_feature_extention(img, donors_id, day_number, donor, max_day, imgname2add):
    extention = []
    #commented out the followings to get rid of the info about which donor = one hot encoding
    # donor one hot encoding
    #extention = np.zeros(len(donors_id))
    #index = donors_id.index(donor)
    #extention[index] = 1
    #extention = list(extention)
    extention.append(day_number / max_day)
    #image order
    '''
    if '(' not in img:
        img_num = 0
    else:
        img_num = img.split('(')[1].split(')')[0]
    extention.append(int(img_num))
    '''
    #ADDs
    if '(' not in img:
        for x in imgname2add[img.split('/')[-1].split('.')[0]]:
            extention.append(float(x)) #the part of the image name that is before the space
    else:
        for x in imgname2add[img.split()[1].split('/')[-1]]:
            extention.append(float(x)) #the part of the image name that is before the space
    return extention
     
    
def modify_features(donors2img2embed, donor2day2imgs): 
    #This function is going to append a one hot encoding, 
    #nth picture of the day, 
    #nth day of de come to the surrent feature vector for each image
    for donor in donor2day2imgs:
        days = [key for key in donor2day2imgs[donor]]
    days.sort()
    max_day = days[-1]
    donors_id = [key for key in donor2day2imgs] 
    for donor in donor2day2imgs:
        daily_imgs = donor2day2imgs[donor] # this is a dict with this format: {day1: [images], day2: [images]...}
        for day in daily_imgs: #iterate for all of the days
            for img in daily_imgs[day]: #iterate through images for each day
                extention = cal_feature_extention(img, donors_id, day, donor, max_day, imgname2add) 
                donors2img2embed[donor][img].extend(extention)
    return donors2img2embed
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--embeding_file', type = str)
    parser.add_argument('--modify', type = str) #True or False
    parser.add_argument('--daily', type = str) #True or False
    parser.add_argument('--cluster_number') # A number
    parser.add_argument('--method') # merge/not-merge
    parser.add_argument('--merge_type') #single or multi (only one donors or multi)
    parser.add_argument('--ADD_file') # the file that include the image names (no space, (, ), and JPG) as the first column and the ADDs as the second column

    args = parser.parse_args()

    embedings_file = args.embeding_file #sys.argv[1] # This should be a pca version the embedings
    modify = args.modify 
    Daily = args.daily 
    num_clusters = int(args.cluster_number)
    method = args.method
    merge_type = args.merge_type
    ADD_file = args.ADD_file

    donors2imgs = {}
    donors2img2embed = {}
    imgname2add = {}

    with open(ADD_file, 'r') as add_file:
        content = csv.reader(add_file, delimiter = '\n')
        for row in content:
            row = row[0].split(',')
            name = row[0]
            add = row[1].strip()
            add = add.replace(' ', ',')
            ADD = ast.literal_eval("[" + add + "]") # this should be a list of temp, humadity and wind ADD
            imgname2add[name] = ADD
        

    with open(embedings_file, 'r') as csv_file:
        data = csv.reader(csv_file,delimiter = '\n')
        vectors = []
        for row in data:
            row = row[0]
            row= row.split('JPG')
            img_name = row[0] + 'JPG'
            embeding = row[1].strip()
            embeding = embeding.replace(' ', ',')
            embeding = ast.literal_eval("[" + embeding[1:-1] + "]") # this embeding is a list now
            donor_id = img_name.split('/Daily')[0].split('/')[-1]
            if donor_id not in donors2img2embed and donor_id not in donors2imgs:
                donors2img2embed[donor_id] = {} 
                donors2imgs[donor_id] = [] # a list for all of the images belonging to the same donor
            donors2img2embed[donor_id][img_name] = embeding 
            # this a dictionary with each donor_id as keys and values are another dictionary
            # with keys being an image and the values being the feature vector for that imag

            donors2imgs[donor_id].append(img_name)

        donors2imgs_sorted = sort_dates(donors2imgs) # this sorts the images for a donor based on their dates
        donor2day2imgs = cal_day_from_deth(donors2imgs_sorted)

        if method == 'merge':
            if modify == 'true':
                donors2img2embed = modify_features(donors2img2embed, donor2day2imgs)
            if merge_type =='single': #only one donor
                day2clus2emb = sequence_finder(donors2img2embed, donor2day2imgs) 
            if merge_type == 'multi': # multiple donor
                day2clus2emb = daily_clustering_per_multidonor(donors2img2embed, donor2day2imgs)


        else:
            if modify == 'true':
                donors2img2embed = modify_features(donors2img2embed, donor2day2imgs)
            
            if Daily == 'true':
                daily_clustering(donors2img2embed, donor2day2imgs)
            elif Daily == 'false':
                cluster(donors2img2embed, donor2day2imgs)
