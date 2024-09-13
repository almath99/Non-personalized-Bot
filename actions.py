# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"


from typing import Any, Text, Dict, List
from rasa_sdk.events import SlotSet
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

class ActionConfirmMovieGenre(Action):

    def name(self) -> Text:
        return "action_confirm_movie_genre"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Retrieve movie genre entity
        movie_genre = tracker.get_slot("movie_genre")  
        
        # If movie_genre entity isn't filled
        if not movie_genre:
            dispatcher.utter_message(text='You did not tell me your preferred movie genre.')
        # Return preferred movie genre
        else:
            dispatcher.utter_message(text=f"Your preferred movie genre is {movie_genre}.")
        return []



import requests
import random
import string
from bs4 import BeautifulSoup
from typing import Union

class ActionMakeMovieRecommendation(Action):
    '''Makes movie recommendations using beautiful soup for web scraping from IMdB'''

    def name(self) -> Text:
        return "action_make_movie_recommendation"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Retrieve movie genre entity
        movie_genre = tracker.get_slot("movie_genre")

        # Scrape movie recommendations for given genre from IMDb
        url = f"https://www.imdb.com/search/title/?title_type=feature&genres={movie_genre.lower()}&start=1&ref_=adv_nxt"
        response = requests.get(url)                          # Send an HTTP GET request to the IMDb website for a list of movies of the specified genre 
        soup = BeautifulSoup(response.text, 'html.parser')    # Use BeautifulSoup to parse the HTML response from the website
        movie_tags = soup.select(".lister-item-header a")     # Extract the movie title tags from the soup object
        movies = [movie.text for movie in movie_tags]         # Create a list of movie titles by iterating through the title tags and extracting their text

        # Filter only movie titles in English, to avoid bot's confusion by checking if each title is composed entirely of printable ASCII characters.
        english_titles = []
        for movie in movies:   
            if all(c in string.printable for c in movie):
                english_titles.append(movie)

        # Choose 5 random English movie titles
        recommendations = random.sample(english_titles, k=5)

        # Make movie recommendation
        if recommendations:
            recommendations_str = "\n- ".join(recommendations)
            dispatcher.utter_message(f"Here are 5 recommendations for {movie_genre} movies:\n- {recommendations_str}")
        else:
            dispatcher.utter_message("Sorry, I could not find any recommendations for that genre.")

        return []



from typing import Any, Dict, List, Text
from rasa_sdk import Action, Tracker
from rasa_sdk.events import Restarted
from rasa_sdk.executor import CollectingDispatcher

class ActionRestart(Action):
    '''Triggers default action_restart action.'''
    def name(self) -> Text:
        return "action_restart"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        return [Restarted()]



class ActionUnlikelyIntent(Action):

    def name(self) -> Text:
        return "action_unlikely_intent"

    async def run(
        self, dispatcher, tracker: Tracker, domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        # Get the detected intent
        detected_intent = tracker.latest_message["intent"].get("name")

        # Define a list of responses for unlikely intents
        unlikely_intent_responses = {
            "greet": ["Hello! How can I assist you today?"],
            "goodbye": ["Goodbye! Feel free to return if you have more questions."],
            "fallback": ["I'm sorry, I didn't understand. Can you please rephrase your question?"],
        }

        # Define a default response for unknown intents
        default_response = ["I'm not sure how to respond to that. Please ask me something else."]

        # Get the response for the detected intent or use the default response
        response = unlikely_intent_responses.get(detected_intent, default_response)

        # Send the response to the user
        dispatcher.utter_message(response[0])

        return []
        

import pymongo
from rasa_sdk import Action

# Connect to your MongoDB server or cluster
client = pymongo.MongoClient("mongodb://chomsky.ilsp.gr:1309/")  # Replace with your MongoDB connection string
db = client["MovieBot"]
collection = db["non_personalized_profiles"]

class ActionCreateUserProfile(Action):
    """ It connects with MongoDB database, 
    creates User profiles and stores them on the database"""
    
    def name(self):
        return "action_create_user_profile"

    def run(self, dispatcher, tracker, domain):
        user_id = tracker.sender_id
        name = tracker.get_slot("name")
        last_name = tracker.get_slot("last_name")
        age = int(tracker.get_slot("age"))  # Convert age to an integer
        hobby = tracker.get_slot("hobby")
        favourite_genre = tracker.get_slot("favourite_genre")

        # Check if the user's profile exists in the collection
        user_profile = collection.find_one({"user_id": user_id})
        if user_profile:
            # Update the user's profile
            collection.update_one(
                {"user_id": user_id},
                {"$set": {"name": name, "last_name": last_name, "age": age, "hobby": hobby, "favourite_genre": favourite_genre}}
            )
        else:
            # Create a new user profile
            new_profile = {
                "user_id": user_id,
                "name": name,
                "last_name": last_name,
                "age": age,
                "hobby": hobby,
                "favourite_genre": favourite_genre
            }
            collection.insert_one(new_profile)

        return []



class UserIdentificationForm(Action):
    """ It collects the name and last name of the user,
        connects with the MongoDB database and searches for the profile there.
        If the name data exist, the the suer is identified."""

    
    def name(self):
        return "user_identification"

    def run(self, dispatcher, tracker, domain):
        name = tracker.get_slot("id_name")
        last_name = tracker.get_slot("id_last_name")

        # Convert the input names to lowercase
        name = name.lower()
        last_name = last_name.lower()
        
        # Query MongoDB to find the user profile
        user_profile = collection.find_one({
            "name": {"$regex": f"^{name}$", "$options": "i"},
            "last_name": {"$regex": f"^{last_name}$", "$options": "i"}
    })

        if user_profile:
            # Extract relevant information from the user profile
            user_profile_id = str(user_profile.get("_id"))
            user_name = user_profile.get("name")
            user_last_name = user_profile.get("last_name")
            user_age = user_profile.get("age")
            user_hobby = user_profile.get("hobby")
            user_favourite_genre = user_profile.get("favourite_genre")

            # Store the user profile ID in a slot for later use
            dispatcher.utter_message(f"Found user profile for {user_name} {user_last_name} (ID: {user_profile_id})")
        
            # Store the user profile ID in a slot for later use
            return [SlotSet("user_profile_id", user_profile_id), SlotSet("age", user_age), SlotSet("hobby", user_hobby), SlotSet("favourite_genre", user_favourite_genre)]
        else:
            dispatcher.utter_message("User profile not found.")
            return []


import openai
from rasa_sdk import Action
from rasa_sdk.events import SlotSet

class ActionGenerateText(Action):
    """ it connects with the GPT-4 API and 
    uses it for language generation and movie recommendations. """

    def name(self):
        return "action_generate_text"
    def run(self, dispatcher, tracker, domain):
        # Replace 'YOUR_API_KEY' with your GPt-4 API key
        api_key = "API-KEY"

        # Retrieve user's preferred movie genre from slot
        user_genre = tracker.get_slot("movie_genre")

        if not user_genre:
            dispatcher.utter_message("I'm sorry, I couldn't identify your preferred movie genre.")
            return []

        # Construct a prompt asking for movie recommendations in the specified genre
        # Zero-shots Approach
        #prompt = f"Recommend two random {user_genre.lower()} movies. Provide demonstrations for each movie with titles, release dates, directors, and main protagonist actors included."
        
        # Few-shots Approach
        prompt = f"Q: Take into account all the movies that exist in IMDB and recommend two random romcom movies and choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, and main protagonist actors included and a small description of the movie in one small sentence. A: Here are two romcom movies you can watch: 1) 10 Thing I hate About You (1999), Directed by Gil Junger. Starring Julia Stiles and Heath Ledger. 2) The Perfect Date (2019), Directed by Chris Nelson. Starring Noah Centineo and Laura Marano. Q: Take into account all the movies movies that exist in IMDB and recommend two random {user_genre.lower()} movies, and choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, and main protagonist actors included and a small description of the movie in one small sentence. Write the movies the one under the other."
     
        # Make a request to the GPT-4 API for text generation
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt}
            ],
            max_tokens=200,
            api_key=api_key
        )

        # Extract the generated text from the response
        generated_text = response['choices'][0]['message']['content']
        

        # Send the generated text as a response
        dispatcher.utter_message(generated_text)

        return [SlotSet("generated_text", generated_text)]


# from rasa_sdk import Action
# from rasa_sdk.events import SlotSet

# class PersonalizedRecommendationAction(Action):
#     """ It keeps the access to the user profile form the above "user_identification" action 
#     and all the information for the user's profile. For the personalized movie recommendation
#     GPT-4 is used. 
#     If the user is under 10 years old, then the action promts GPT to recommenda only kid movies.
#     If the user is under 18 years old, then the action prompts GPT to recommend teen appropriate movies.
#     If the user is an adult then GPT can recommend any movie.
#     For all the age groups the hobby/ interest of each user is also considered.
#     The genre chosen for this recommendation is the favourite_genre of the user, as it is noted in 
#     the MongoDB database."""

#     def name(self):
#         return "action_personalized_recommendation"

#     def run(self, dispatcher, tracker, domain):
#         # Get user information from slots
#         user_age = tracker.get_slot("age")
#         user_favourite_genre = tracker.get_slot("favourite_genre")
#         user_hobby = tracker.get_slot("hobby")

#         if user_age and user_favourite_genre:
#             # Create a prompt for GPT-4
#             if user_age < 10:
                
#                 # Blended Prompt
#                 prompt = f"Q: Take into account all the movies on IMDB for the comedy genre and recommend two comedy movies, that are acceptable for a 9-year-old child who enjoys comedy films and has an interest in animals. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. A: Since you are 9 years old and you like comedy movies and animals, then you will probably love these two movies: 1) The Cat from Outer Space (1978), Directed by Norman Tokar. Starring Ken Berry, Sandy Duncan (and the voice of Ronnie Schell as Jake. A charming extraterrestrial cat with unique abilities befriends a group of humans as they work together to repair his spaceship and evade government agents. 2) The Adventures of Rocky and Bullwinkle (2000), Directed by Des McAnuff. Starring June Foray (voice of Rocky), Keith Scott (voice of Bullwinkle). It follows the iconic animated duo as they venture into the real world to stop the evil plans of their arch-nemeses, Boris and Natasha. Q: Take into account all the movies on IMDB for the comedy genre and recommend two comedy movies, that are acceptable for a 9-year-old child who enjoys comedy films and has an interest in animals. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. A: Since you are 9 years old and you like comedy movies and animals, then you will probably love these two movies: 1) Cats & Dogs (2001), Directed by Lawrence Guterman. Voice cast includes Tobey Maguire and Alec Baldwin. A secret war between cats and dogs unfolds, revealing the furry agents and gadgets they use in their comedic battle for control. 2) G-Force (2009), Directed by Hoyt Yeatman. Voice cast includes Sam Rockwell and Penélope Cruz. It follows a squad of highly trained guinea pigs as they embark on a mission to save the world, blending action and humor in an entertaining adventure for animal-loving comedy enthusiasts. Q: Take into account all the movies on IMDB for the comedy genre and recommend two comedy movies, that are acceptable for a 9-year-old child who enjoys comedy films and has an interest in animals. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. A: Since you are 9 years old and you like comedy movies and animals, then you will probably love these two movies: 1) The Penguins of Madagascar (2014), Directed by Eric Darnell and Simon J. Smith. Voice casting includes Tom McGrath, Chris Miller, Christopher Knights, Conrad Vernon. It follows the hilarious adventures of the four penguins as they embark on a mission to save their fellow zoo animals. 2) Dr. Dolittle 2 (2001), Directed by Steve Carr. Starring Eddie Murphy. the beloved doctor who can talk to animals teams up with a beaver to save a forest, combining comedy and heartwarming moments in a delightful family-friendly film. Q: Take into account all the movies on IMDB for the {user_favourite_genre} genre and recommend two {user_favourite_genre} movies, that are acceptable for a {user_age} child who enjoys {user_favourite_genre} films and has an interest in {user_hobby}. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. Write each movie under the other."

#             elif user_age < 18:
#                 # Blended Prompt
#                 prompt = f"Q: Take into account all the movies on IMDB for the romcom genre and recommend two romcom movies, that are acceptable for a 15-year-old teen who enjoys romcom films and has an interest in dancing. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. A: Since you are 15 years old and you like romcom movies and dancing, then you will probably love these two movies: 1) Step Up (2006), Directed by Anne Fletcher. Starring Channing Tatum and Jenna Dewan. A talented street dancer and a classically trained dancer join forces to create a dynamic fusion of dance styles, blending romance and impressive choreography. 2) La La Land (2016), Directed by Damien Chazelle. Starring Ryan Gosling and Emma Stone. A modern musical that follows the love story between a jazz musician and an aspiring actress in Los Angeles, beautifully combining romance, music, and vibrant dance sequences. Q: Take into account all the movies on IMDB for the romcom genre and recommend two romcom movies, that are acceptable for a 15-year-old teen who enjoys romcom films and has an interest in dancing. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. A: Since you are 15 years old and you like romcom movies and dancing, then you will probably love these two movies: 1) Billy Elliot (2000), Directed by Stephen Daldry. Starring Jamie Bell. It tells the inspiring story of a young boy in a northern English mining town who discovers his passion for ballet against the backdrop of societal expectations and the coal miners' strike. 2) Polina (2016), Directed by Valérie Müller and Angelin Preljocaj. Starring Anastasia Shevtsova. A talented Russian ballet dancer faces personal and professional challenges as she explores her artistic identity and pursues her dreams in the competitive world of dance. Q: Take into account all the movies on IMDB for the romcom genre and recommend two romcom movies, that are acceptable for a 15-year-old teen who enjoys romcom films and has an interest in dancing. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. A: Since you are 15 years old and you like romcom movies and dancing, then you will probably love these two movies: 1) Save the Last Dance (2001), Directed by Thomas Carter. Starring Julia Stiles and Sean Patrick Thomas. It follows a young aspiring dancer who navigates racial tensions and personal challenges while pursuing her dreams in a new city, blending romance and dance. 2) Black Swan (2010), Directed by Darren Aronofsky. Starring Natalie Portman and Mila Kunis. It delves into the intense and psychological world of ballet, telling the haunting story of a ballerina's descent into madness as she prepares for a demanding role, offering a gripping and dark take on the dance genre. Q: Take into account all the movies on IMDB for the {user_favourite_genre} genre and recommend two {user_favourite_genre} movies, that are acceptable for a {user_age} teen who enjoys {user_favourite_genre} films and has an interest in {user_hobby}. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. Write each movie under the other."

#             else:
#                 # Blended Prompt
#                 prompt = f"Q: Take into account all the movies on IMDB for the crime genre and recommend two crime movies, that are acceptable for a 35-year-old adult who enjoys crime films and has an interest in medicine. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. A: Since you are 35 years old and you like crime movies and medicine, then you will probably love these two movies: 1) Contagion (2011), Directed by Steven Soderbergh. Starring Matt Damon. As a lethal virus spreads globally, medical professionals and government officials race against time to understand and contain the outbreak in this gripping, medically focused thriller. 2) Se7en (1995), Directed by David Fincher. Starring Morgan Freeman as Detective William Somerset and Brad Pitt as Detective David Mills. Detectives Mills and Somerset hunt a serial killer who uses the seven deadly sins as his motives in a dark and intense psychological thriller. Q: Take into account all the movies on IMDB for the crime genre and recommend two crime movies, that are acceptable for a 35-year-old adult who enjoys crime films and has an interest in medicine. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. A: Since you are 35 years old and you like crime movies and medicine, then you will probably love these two movies: 1) The Departed (2006), Directed by Martin Scorsese. Starring Leonardo DiCaprio and Matt Damon. In this crime drama, an undercover cop and a mole in the police force try to identify each other while infiltrating an Irish gang in Boston, leading to a complex web of deception and suspense. 2) Outbreak (1995), Directed by Wolfgang Petersen. Starring Dustin Hoffman and Rene Russo. A team of doctors and military personnel races to contain a deadly virus outbreak in a small town, exploring themes of science, ethics, and government involvement in a thrilling crime-tinged medical drama. Q: Take into account all the movies on IMDB for the crime genre and recommend two crime movies, that are acceptable for a 35-year-old adult who enjoys crime films and has an interest in medicine. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. A: Since you are 35 years old and you like crime movies and medicine, then you will probably love these two movies: 1) Mystic River (2003), Directed by Clint Eastwood. Starring Sean Penn and Tim Robbins. The lives of childhood friends take a tragic turn when a murder investigation reunites them, uncovering dark secrets and unresolved trauma in a gritty and emotionally charged crime drama. 2) Awakenings (1990), Directed by Penny Marshall. Starring Robert de Niro and Robin Williams. Based on a true story, a dedicated doctor's use of an experimental drug awakens catatonic patients, exploring the ethical dilemmas and human connections in the intersection of medicine and crime. Q: Take into account all the movies on IMDB for the {user_favourite_genre} genre and recommend two {user_favourite_genre} movies, that are acceptable for a {user_age} adult who enjoys {user_favourite_genre} films and has an interest in {user_hobby}. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. Write each movie under the other."
            

#             # Replace 'YOUR_API_KEY' with your GPT-3.5 Turbo API key
#             api_key = "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"
            
#                 # Make a request to the GPT-4 API for text generation
#             response = openai.ChatCompletion.create(
#                 model="gpt-4",
#                 messages=[
#                     {"role": "system", "content": prompt}
#                 ],
#                 max_tokens=200,
#                 api_key=api_key
#             )

#             # Extract the generated text from the response
#             generated_text = response['choices'][0]['message']['content']

#             # Send the generated text as a response
#             dispatcher.utter_message(generated_text)

#             return [SlotSet("generated_text", generated_text)]
#         else:
#             dispatcher.utter_message("I need both your age and favorite genre to provide recommendations.")
#             return []




# import openai
# from rasa_sdk import Action
# from rasa_sdk.events import SlotSet

# class ActionPersonalizedRecommendationGenre(Action):
#     """ Same as "action_personalized_recommendation", but it the recommendation isn't based 
#     on the users' favourite_genre, but the movie_genre that they choose."""
    
#     def name(self):
#         return "action_personalized_recommendation_genre"

#     def run(self, dispatcher, tracker, domain):
        
#         # Replace 'YOUR_API_KEY' with your GPT-3.5 Turbo API key
#         api_key = "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"

#         # Retrieve user input and slots
#         user_age = tracker.get_slot("age")
#         user_genre = tracker.get_slot("movie_genre")
#         user_hobby = tracker.get_slot("hobby")

#         if user_age and user_genre:
#                 # Create a prompt for GPT-3.5 Turbo based on user's age, genre, and hobby
#             if user_age < 10:
#                 # Blended Prompt
#                 prompt = f"Q: Take into account all the movies on IMDB for the comedy genre and recommend two comedy movies, that are acceptable for a 9-year-old child who enjoys comedy films and has an interest in animals. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. A: Since you are 9 years old and you like comedy movies and animals, then you will probably love these two movies: 1) The Cat from Outer Space (1978), Directed by Norman Tokar. Starring Ken Berry, Sandy Duncan (and the voice of Ronnie Schell as Jake. A charming extraterrestrial cat with unique abilities befriends a group of humans as they work together to repair his spaceship and evade government agents. 2) The Adventures of Rocky and Bullwinkle (2000), Directed by Des McAnuff. Starring June Foray (voice of Rocky), Keith Scott (voice of Bullwinkle). It follows the iconic animated duo as they venture into the real world to stop the evil plans of their arch-nemeses, Boris and Natasha. Q: Take into account all the movies on IMDB for the comedy genre and recommend two comedy movies, that are acceptable for a 9-year-old child who enjoys comedy films and has an interest in animals. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. A: Since you are 9 years old and you like comedy movies and animals, then you will probably love these two movies: 1) Cats & Dogs (2001), Directed by Lawrence Guterman. Voice cast includes Tobey Maguire and Alec Baldwin. A secret war between cats and dogs unfolds, revealing the furry agents and gadgets they use in their comedic battle for control. 2) G-Force (2009), Directed by Hoyt Yeatman. Voice cast includes Sam Rockwell and Penélope Cruz. It follows a squad of highly trained guinea pigs as they embark on a mission to save the world, blending action and humor in an entertaining adventure for animal-loving comedy enthusiasts. Q: Take into account all the movies on IMDB for the comedy genre and recommend two comedy movies, that are acceptable for a 9-year-old child who enjoys comedy films and has an interest in animals. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. A: Since you are 9 years old and you like comedy movies and animals, then you will probably love these two movies: 1) The Penguins of Madagascar (2014), Directed by Eric Darnell and Simon J. Smith. Voice casting includes Tom McGrath, Chris Miller, Christopher Knights, Conrad Vernon. It follows the hilarious adventures of the four penguins as they embark on a mission to save their fellow zoo animals. 2) Dr. Dolittle 2 (2001), Directed by Steve Carr. Starring Eddie Murphy. the beloved doctor who can talk to animals teams up with a beaver to save a forest, combining comedy and heartwarming moments in a delightful family-friendly film. Q: Take into account all the movies on IMDB for the {user_genre} genre and recommend two {user_genre} movies, that are acceptable for a {user_age} child who enjoys {user_genre} films and has an interest in {user_hobby}. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. Write each movie under the other."
#             elif user_age < 18:
#                 # Blended Prompt
#                 prompt = f"Q: Take into account all the movies on IMDB for the romcom genre and recommend two romcom movies, that are acceptable for a 15-year-old teen who enjoys romcom films and has an interest in dancing. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. A: Since you are 15 years old and you like romcom movies and dancing, then you will probably love these two movies: 1) Step Up (2006), Directed by Anne Fletcher. Starring Channing Tatum and Jenna Dewan. A talented street dancer and a classically trained dancer join forces to create a dynamic fusion of dance styles, blending romance and impressive choreography. 2) La La Land (2016), Directed by Damien Chazelle. Starring Ryan Gosling and Emma Stone. A modern musical that follows the love story between a jazz musician and an aspiring actress in Los Angeles, beautifully combining romance, music, and vibrant dance sequences. Q: Take into account all the movies on IMDB for the romcom genre and recommend two romcom movies, that are acceptable for a 15-year-old teen who enjoys romcom films and has an interest in dancing. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. A: Since you are 15 years old and you like romcom movies and dancing, then you will probably love these two movies: 1) Billy Elliot (2000), Directed by Stephen Daldry. Starring Jamie Bell. It tells the inspiring story of a young boy in a northern English mining town who discovers his passion for ballet against the backdrop of societal expectations and the coal miners' strike. 2) Polina (2016), Directed by Valérie Müller and Angelin Preljocaj. Starring Anastasia Shevtsova. A talented Russian ballet dancer faces personal and professional challenges as she explores her artistic identity and pursues her dreams in the competitive world of dance. Q: Take into account all the movies on IMDB for the romcom genre and recommend two romcom movies, that are acceptable for a 15-year-old teen who enjoys romcom films and has an interest in dancing. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. A: Since you are 15 years old and you like romcom movies and dancing, then you will probably love these two movies: 1) Save the Last Dance (2001), Directed by Thomas Carter. Starring Julia Stiles and Sean Patrick Thomas. It follows a young aspiring dancer who navigates racial tensions and personal challenges while pursuing her dreams in a new city, blending romance and dance. 2) Black Swan (2010), Directed by Darren Aronofsky. Starring Natalie Portman and Mila Kunis. It delves into the intense and psychological world of ballet, telling the haunting story of a ballerina's descent into madness as she prepares for a demanding role, offering a gripping and dark take on the dance genre. Q: Take into account all the movies on IMDB for the {user_genre} genre and recommend two {user_genre} movies, that are acceptable for a {user_age} teen who enjoys {user_genre} films and has an interest in {user_hobby}. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. Write each movie under the other."
#             else:
#                 # Blended Prompt
#                 prompt = f"Q: Take into account all the movies on IMDB for the crime genre and recommend two crime movies, that are acceptable for a 35-year-old adult who enjoys crime films and has an interest in medicine. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. A: Since you are 35 years old and you like crime movies and medicine, then you will probably love these two movies: 1) Contagion (2011), Directed by Steven Soderbergh. Starring Matt Damon. As a lethal virus spreads globally, medical professionals and government officials race against time to understand and contain the outbreak in this gripping, medically focused thriller. 2) Se7en (1995), Directed by David Fincher. Starring Morgan Freeman as Detective William Somerset and Brad Pitt as Detective David Mills. Detectives Mills and Somerset hunt a serial killer who uses the seven deadly sins as his motives in a dark and intense psychological thriller. Q: Take into account all the movies on IMDB for the crime genre and recommend two crime movies, that are acceptable for a 35-year-old adult who enjoys crime films and has an interest in medicine. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. A: Since you are 35 years old and you like crime movies and medicine, then you will probably love these two movies: 1) The Departed (2006), Directed by Martin Scorsese. Starring Leonardo DiCaprio and Matt Damon. In this crime drama, an undercover cop and a mole in the police force try to identify each other while infiltrating an Irish gang in Boston, leading to a complex web of deception and suspense. 2) Outbreak (1995), Directed by Wolfgang Petersen. Starring Dustin Hoffman and Rene Russo. A team of doctors and military personnel races to contain a deadly virus outbreak in a small town, exploring themes of science, ethics, and government involvement in a thrilling crime-tinged medical drama. Q: Take into account all the movies on IMDB for the crime genre and recommend two crime movies, that are acceptable for a 35-year-old adult who enjoys crime films and has an interest in medicine. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. A: Since you are 35 years old and you like crime movies and medicine, then you will probably love these two movies: 1) Mystic River (2003), Directed by Clint Eastwood. Starring Sean Penn and Tim Robbins. The lives of childhood friends take a tragic turn when a murder investigation reunites them, uncovering dark secrets and unresolved trauma in a gritty and emotionally charged crime drama. 2) Awakenings (1990), Directed by Penny Marshall. Starring Robert de Niro and Robin Williams. Based on a true story, a dedicated doctor's use of an experimental drug awakens catatonic patients, exploring the ethical dilemmas and human connections in the intersection of medicine and crime. Q: Take into account all the movies on IMDB for the {user_genre} genre and recommend two {user_genre} movies, that are acceptable for a {user_age} adult who enjoys {user_genre} films and has an interest in {user_hobby}. Choose a mix of famous and not so famous movies. Provide demonstrations for each movie with titles, release dates, directors, main protagonist actors and a small description of the movie in only one small sentence. Make sure the recommendations are unique. Write each movie under the other."

#                 # Make a request to the GPT-4 API for text generation
#             response = openai.ChatCompletion.create(
#                 model="gpt-4",
#                 messages=[
#                     {"role": "system", "content": prompt}
#                 ],
#                 max_tokens=200,
#                 api_key=api_key
#             )

#             # Extract the generated text from the response
#             generated_text = response['choices'][0]['message']['content']

#             # Send the generated text as a response
#             dispatcher.utter_message(generated_text)

#             return [SlotSet("generated_text", generated_text)]
#         else:
#             dispatcher.utter_message("I need both your age and favorite genre to provide recommendations.")
#             return []



